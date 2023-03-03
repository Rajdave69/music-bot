import datetime
import random
import discord
from discord.ext import commands
import wavelink
from backend import wavelink_host, wavelink_password, wavelink_port, log, vc_exists, embed_template, \
    owner_ids, error_template
import sqlite3
import discord.ext.pages


class Main(discord.Cog):
    def __init__(self, client):
        self.client = client
        self.con = sqlite3.connect("./data/data.db")
        self.cur = self.con.cursor()

    @commands.Cog.listener()
    async def on_ready(self):
        print("Connected to Discord!")
        await self.connect_nodes()

    async def connect_nodes(self):
        await self.client.wait_until_ready()
        await wavelink.NodePool.create_node(
            bot=self.client,
            host=wavelink_host,
            port=wavelink_port,
            password=wavelink_password
        )

    @commands.slash_command()
    async def play(self, ctx, song: str):
        vc = ctx.voice_client

        if not vc:
            try:
                vc = await ctx.author.voice.channel.connect(cls=wavelink.Player)
                await vc.set_volume(50)
            except AttributeError:
                return await ctx.respond(embed=error_template("You are not connected to a voice channel."),
                                         ephemeral=True)

        if ctx.author.voice is None:
            return await ctx.respond(embed=error_template("You are not connected to a voice channel."), ephemeral=True)
        if ctx.author.voice.channel.id != vc.channel.id:
            return await ctx.respond(embed=error_template("You are not in the same voice channel as me."),
                                     ephemeral=True)

        try:
            song = await wavelink.YouTubeTrack.search(song, return_first=True)
        except:
            await ctx.respond(embed=error_template("No songs found."))
            await vc.disconnect()
            return

        if song.is_stream():
            await ctx.respond("Streams are not supported.")
            await vc.disconnect()
            return

        if song.duration > 600:
            print(ctx.author.id, owner_ids)
            if str(ctx.author.id) not in owner_ids:
                if not ctx.author.guild_permissions.manage_guild or not ctx.author.guild_permissions.manage_channels:
                    await ctx.respond("Songs longer than 10 minutes are not supported.")
                    await vc.disconnect()
                    return

        if not song:
            await ctx.respond("No songs found.")
            await vc.disconnect()
            return

        duration = datetime.timedelta(seconds=song.duration)

        embed = embed_template()
        embed.title = "Now Playing"
        embed.description = f"[{song.title}]({song.uri})"
        embed.add_field(name="Duration", value=f"{str(duration)[2:]}", inline=True)
        embed.add_field(name="Requested by", value=ctx.author.mention, inline=True)

        thumbnail = f"https://img.youtube.com/vi/{song.identifier}/mqdefault.jpg"
        log.debug(thumbnail)
        embed.set_image(url=thumbnail)

        if not vc.is_playing():
            await vc.play(song)

        else:
            vc.queue.put(song)
            embed.fields[0].name = "Added to Queue"

        embed.add_field(name="Queue Position", value=f"{vc.queue.count}", inline=True)
        await ctx.respond(embed=embed)

    @commands.slash_command()
    async def skip(self, ctx):
        vc = ctx.voice_client

        if not await vc_exists(ctx):
            return

        # play the next song from the queue
        if not vc.queue.is_empty:
            # Seek the current song to the end
            await vc.seek(vc.source.duration * 1000)

            embed = embed_template()
            embed.title = "Skipped"
            embed.description = "Successfully skipped the current song."
            embed.add_field(name="Next Song", value=f"`{vc.queue[0]}`",
                            inline=False)

        else:
            return await ctx.respond(embed=error_template("Could not skip the Current Song. The Queue is empty!"),
                                     ephemeral=True)

        await ctx.respond(embed=embed)

    @commands.slash_command()
    async def stop(self, ctx):
        vc = ctx.voice_client

        if not await vc_exists(ctx):
            return
        await vc.disconnect()

        embed = embed_template()
        embed.title = "Disconnected"
        embed.description = "Successfully disconnected from the voice channel."

        await ctx.respond(embed=embed)

    @commands.slash_command()
    async def volume(self, ctx, volume: int):
        vc = ctx.voice_client

        if not await vc_exists(ctx):
            return

        if 0 < volume <= 100:
            embed = embed_template()
            embed.title = "Volume"
            embed.description = f"Successfully changed the volume."

            embed.add_field(name="Old Volume", value=f"{vc.volume}", inline=True)
            await vc.set_volume(volume)
            embed.add_field(name="New Volume", value=f"{volume}", inline=True)

        else:
            return ctx.respond(embed=error_template("The volume must be between 1 and 100."), ephemeral=True)

        await ctx.respond(embed=embed)

    @commands.slash_command(name="queue")
    async def queue(self, ctx):
        vc = ctx.voice_client

        if not await vc_exists(ctx):
            return

        embed = embed_template()
        embed.title = "Queue"
        embed.add_field(name="Now Playing", value=f"[{vc.source.title}]({vc.source.uri})")

        embed_list = []
        total_duration = 0

        for i, song in enumerate(vc.queue):
            duration = datetime.timedelta(seconds=song.duration)
            total_duration += song.duration
            embed.add_field(name=f"{i + 1}. `{song.title}`", value=f"Duration: {str(duration)[2:]}", inline=False)

            if (i + 1) % 10 == 0:
                embed_list.append(embed.copy())
                embed.clear_fields()
            elif i == vc.queue.count - 1:
                embed_list.append(embed.copy())

        if len(embed_list) > 0:
            embed_list[0].description = f"Total Queue Duration: {str(datetime.timedelta(seconds=total_duration))}"
            paginator = discord.ext.pages.Paginator(
                pages=embed_list, disable_on_timeout=True, timeout=120
            )
            await paginator.respond(ctx.interaction, ephemeral=False)
        else:
            await ctx.respond(embed=embed)

    @commands.slash_command(name="pause")
    async def pause(self, ctx):
        vc = ctx.voice_client

        if not await vc_exists(ctx):
            return
        await vc.set_pause(not vc.is_paused())

        embed = embed_template()
        embed.title = "Paused" if vc.is_paused() else "Resumed"
        embed.description = f"Successfully {'paused' if vc.is_paused() else 'resumed'} the player."
        await ctx.respond(embed=embed)

    @commands.slash_command(name="resume")
    async def resume(self, ctx):
        vc = ctx.voice_client

        if not await vc_exists(ctx):
            return
        await vc.set_pause(not vc.is_paused())

        embed = embed_template()
        embed.title = "Paused" if vc.is_paused() else "Resumed"
        embed.description = f"Successfully {'paused' if vc.is_paused() else 'resumed'} the player."
        await ctx.respond(embed=embed)

    @commands.slash_command()
    async def shuffle(self, ctx):
        vc = ctx.voice_client

        if not await vc_exists(ctx):
            return
        song_list = []

        for i in range(vc.queue.count):
            song_list.append(vc.queue.get())

        random.shuffle(song_list)
        vc.queue.clear()

        for song in song_list:
            vc.queue.put(song)

        embed = embed_template()
        embed.title = "Shuffled"
        embed.description = "Successfully shuffled the queue."
        await ctx.respond(embed=embed)

    async def cog_check(self, ctx) -> bool:
        """A local check which applies to all commands in this cog."""
        if not ctx.guild:
            raise commands.NoPrivateMessage
        return True


def setup(client):
    client.add_cog(Main(client))
