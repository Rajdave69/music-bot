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
            except AttributeError:
                return await ctx.respond("You are not connected to a voice channel.")

        if ctx.author.voice.channel.id != vc.channel.id:
            return await ctx.respond("You are not in the same voice channel as me.")

        song = await wavelink.YouTubeTrack.search(song, return_first=True)

        if song.is_stream():
            await ctx.respond("Streams are not supported.")
            await vc.disconnect()
            return

        if song.duration > 600:
            print(ctx.author.id, owner_ids)
            if str(ctx.author.id) not in owner_ids:
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

        if not vc:
            return await ctx.respond("I am not connected to a voice channel.")

        if not vc.is_playing():
            return await ctx.respond("I am not playing anything.")

        # play the next song from the queue
        if vc.queue.count > 0:
            # seek the current song to the end
            await vc.stop()
            await ctx.respond("Skipped the current song.")
        else:
            await ctx.respond("There are no more songs in the queue.")

    @commands.slash_command()
    async def stop(self, ctx):
        vc = ctx.voice_client

        if not vc:
            return await ctx.respond("I am not connected to a voice channel.")

        if not vc.is_playing():
            return await ctx.respond("I am not playing anything.")

        await vc.disconnect()
        vc.queue.clear()

    @commands.slash_command()
    async def volume(self, ctx, volume: int):
        vc = ctx.voice_client

        if not vc:
            return await ctx.respond("I am not connected to a voice channel.")

        if not vc.is_playing():
            return await ctx.respond("I am not playing anything.")

        if 0 < volume > 100:
            await vc.set_volume(volume / 100)
            await ctx.respond(f"Set the volume to {volume}%")

        await vc.set_volume(volume)
        await ctx.respond(f"Set the volume to {volume}.")

    @commands.slash_command(name="queue", aliases=['currentplaying'])
    async def queue(self, ctx):
        vc = ctx.voice_client

        if not vc:
            return await ctx.respond("I am not connected to a voice channel.")

        if not vc.is_playing():
            return await ctx.respond("I am not playing anything.")

        embed = discord.Embed(title="Music Queue")
        embed.set_footer(text=embed_footer)

        embed.add_field(name="Now Playing", value=f"[{vc.source.title}]({vc.source.uri})")

        for i, song in enumerate(vc.queue):
            duration = datetime.timedelta(seconds=song.duration)
            embed.add_field(name=f"{i + 1}. `{song.title}`", value=f"Duration: {str(duration)[2:]}", inline=False)

        await ctx.respond(embed=embed)

    @commands.slash_command(name="resume")
    @commands.slash_command(name="pause")
    async def pause_resume(self, ctx):
        vc = ctx.voice_client

        if not vc:
            return await ctx.respond("I am not connected to a voice channel.")

        if not vc.is_playing():
            return await ctx.respond("I am not playing anything.")

        await vc.set_pause(not vc.paused)
        await ctx.respond("Paused/Resumed the music.")

    @commands.slash_command()
    async def shuffle(self, ctx):  # TODO: test this
                         discord.OptionChoice("ChannelMix", value="ChannelMix"),
                         discord.OptionChoice("LowPass", value="LowPass")
                     ])
                     ):
        vc = ctx.voice_client

        if not vc:
            return await ctx.respond("I am not connected to a voice channel.")

        if not vc.is_playing():
            return await ctx.respond("I am not playing anything.")

    async def cog_check(self, ctx) -> bool:
        """A local check which applies to all commands in this cog."""
        if not ctx.guild:
            raise commands.NoPrivateMessage
        return True


def setup(client):
    client.add_cog(Main(client))
