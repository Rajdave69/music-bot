import copy
import datetime
import random
from discord.ext import commands
from discord import app_commands
import wavelink
from backend import lavalink_creds, log, vc_exists, embed_template, \
    owner_ids, error_template
import sqlite3
import paginator


class Main(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.con = sqlite3.connect("./data/data.db")
        self.cur = self.con.cursor()

    @commands.Cog.listener()
    async def on_ready(self):
        log.info("Cog: Main.py Loaded")
        try:
            await self.connect_nodes()
        except Exception as e:
            log.critical(f"Failed to connect to nodes.\n{e}")
        # await self.client.tree.sync()

    async def connect_nodes(self):
        await self.client.wait_until_ready()
        nodes = []

        for cred in lavalink_creds.keys():
            nodes.append(wavelink.Node(uri=cred.strip().replace("|", ":"), password=lavalink_creds[cred]))

        await wavelink.NodePool.connect(client=self.client, nodes=nodes)
        log.info(f"Connected to {len(nodes)} node(s).")

    @app_commands.command()
    async def play(self, interaction, song: str):
        vc = interaction.guild.voice_client

        if not vc:
            try:
                vc = await interaction.user.voice.channel.connect(cls=wavelink.Player)
                await vc.set_volume(50)
            except AttributeError:
                return await interaction.response.send_message(
                    embed=error_template("You are not connected to a voice channel."),
                    ephemeral=True)

        if interaction.user.voice is None:
            return await interaction.response.send_message(
                embed=error_template("You are not connected to a voice channel."), ephemeral=True)
        if interaction.user.voice.channel.id != vc.channel.id:
            return await interaction.response.send_message(
                embed=error_template("You are not in the same voice channel as me."),
                ephemeral=True)

        try:
            song = await wavelink.YouTubeTrack.search(song, return_first=True)
        except:
            await interaction.response.send_message(embed=error_template("No songs found."))
            return # todo add some sort of disconnect ONLY IF queue empty

        if song.is_stream:
            await interaction.response.send_message(embed=error_template("Streams are not supported."))
            return # todo add some sort of disconnect ONLY IF queue empty

        if song.duration / 1000 > 600:
            if str(interaction.user.id) not in owner_ids:
                if not interaction.user.guild_permissions.manage_guild or not interaction.user.guild_permissions.manage_channels:
                    await interaction.response.send_message("Songs longer than 10 minutes are not supported.")
                    return  # todo add some sort of disconnect ONLY IF queue empty

        duration = str(datetime.timedelta(seconds=song.duration / 1000))

        embed = embed_template()
        embed.title = "Now Playing"
        embed.description = f"[{song.title}]({song.uri})"
        embed.add_field(name="Duration", value=f"{duration if duration[0] != '0' else duration[2:7]}", inline=True)
        embed.add_field(name="Requested by", value=interaction.user.mention, inline=True)

        thumbnail = f"https://img.youtube.com/vi/{song.identifier}/mqdefault.jpg"
        log.debug(thumbnail)
        embed.set_image(url=thumbnail)
        # thumbnail = await song.fetch_thumbnail() # todo wavelink 2.0 feature

        if not vc.is_playing():
            await vc.play(song)  # DO NOT COMMIT THIS payload_args={"skipSegments": ["music_offtopic"]}

        else:
            vc.queue.put(song)
            embed.fields[0].name = "Added to Queue"

        embed.add_field(name="Queue Position", value=f"{vc.queue.count}", inline=True)
        await interaction.response.send_message(embed=embed)

    @app_commands.command()
    async def skip(self, interaction, amount: int = 1):
        vc = interaction.guild.voice_client

        if not await vc_exists(interaction):
            return

        # play the next song from the queue
        if not vc.queue.is_empty:
            # Seek the current song to the end
            for _ in range(amount):
                if not vc.queue.is_empty:
                    await vc.seek(vc.position * 1000)
                else:
                    break

            embed = embed_template()
            embed.title = "Skipped"
            embed.description = "Successfully skipped the current song."
            embed.add_field(name="Next Song", value=f"`{vc.queue[0]}`",
                            inline=False)

        else:
            return await interaction.response.send_message(
                embed=error_template("Could not skip the Current Song. The Queue is empty!"),
                ephemeral=True)

        await interaction.response.send_message(embed=embed)

    @app_commands.command()
    async def stop(self, interaction):
        vc = interaction.guild.voice_client

        if not await vc_exists(interaction):
            return
        await vc.disconnect()

        embed = embed_template()
        embed.title = "Disconnected"
        embed.description = "Successfully disconnected from the voice channel."

        await interaction.response.send_message(embed=embed)

    @app_commands.command()
    async def volume(self, interaction, volume: int):
        vc = interaction.guild.voice_client

        if not await vc_exists(interaction):
            return

        if 0 < volume <= 100:
            embed = embed_template()
            embed.title = "Volume"
            embed.description = f"Successfully changed the volume."

            embed.add_field(name="Old Volume", value=f"{vc.volume}", inline=True)
            await vc.set_volume(volume)
            embed.add_field(name="New Volume", value=f"{volume}", inline=True)

        else:
            return interaction.response.send_message(
                embed=error_template("The volume must be between 1 and 100."),
                ephemeral=True
            )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="queue")
    async def queue(self, interaction):
        vc = interaction.guild.voice_client

        if not await vc_exists(interaction):
            return

        embed = embed_template()
        embed.title = "Queue"
        embed.add_field(name="Now Playing", value=f"[{vc.current.title}]({vc.current.uri})")

        embed_list = []
        total_duration = 0

        for i, song in enumerate(vc.queue):
            duration = datetime.timedelta(seconds=song.duration / 1000)
            total_duration += song.duration / 1000
            embed.add_field(name=f"{i + 1}. `{song.title}`", value=f"Duration: {str(duration)}", inline=False)

            if (i + 1) % 10 == 0:
                embed_list.append(copy.deepcopy(embed))
                embed.clear_fields()
            if i == vc.queue.count - 1:
                # if vc.queue.count - 1 < 10:
                #     continue
                embed_list.append(copy.deepcopy(embed))

        if embed_list:
            if not embed_list[-1].fields:
                embed_list.pop(-1)

        if len(embed_list) > 0:
            embed_list[0].description = f"Total Queue Duration: {str(datetime.timedelta(seconds=total_duration))}"
            await paginator.Simple(timeout=120).start(interaction, pages=embed_list)

        else:
            await interaction.response.send_message(embed=embed)

    @app_commands.command(name="pause")
    async def pause(self, interaction):
        vc = interaction.guild.voice_client

        if not await vc_exists(interaction):
            return
        if vc.is_paused():
            await vc.resume()
        else:
            await vc.pause()

        embed = embed_template()
        embed.title = "Paused" if vc.is_paused() else "Resumed"
        embed.description = f"Successfully {'paused' if vc.is_paused() else 'resumed'} the player."
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="resume")
    async def resume(self, interaction):
        vc = interaction.guild.voice_client

        if not await vc_exists(interaction):
            return
        if vc.is_paused():
            await vc.resume()
        else:
            await vc.pause()

        embed = embed_template()
        embed.title = "Paused" if vc.is_paused() else "Resumed"
        embed.description = f"Successfully {'paused' if vc.is_paused() else 'resumed'} the player."
        await interaction.response.send_message(embed=embed)

    @app_commands.command()
    async def shuffle(self, interaction):
        vc = interaction.guild.voice_client

        if not await vc_exists(interaction):
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
        await interaction.response.send_message(embed=embed)

    async def cog_check(self, interaction) -> bool:
        """A local check which applies to all commands in this cog."""
        if not interaction.guild:
            raise commands.NoPrivateMessage
        return True


async def setup(client):
    await client.add_cog(Main(client))
