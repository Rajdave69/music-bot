import datetime
import discord
from discord.ext import commands
import wavelink
from backend import wavelink_host, wavelink_password, wavelink_port, embed_footer, log, embed_color, embed_url, \
    embed_header
import aiohttp
import sqlite3


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
            vc.disconnect()
            return

        if song.duration > 600:
            await ctx.respond("Songs longer than 10 minutes are not supported.")
            vc.disconnect()
            return

        duration = datetime.timedelta(seconds=song.duration)

        embed = discord.Embed(title="Music")
        embed.add_field(name="Now Playing", value=f"[{song.title}]({song.uri})")
        embed.add_field(name="Duration", value=f"{str(duration)[2:]}", inline=False)
        async with aiohttp.ClientSession() as session:
            async with session.get(song.thumbnail) as resp:
                if resp.status == 200:
                    embed.set_image(url=song.thumbnail)
                else:
                    embed.set_image(url=song.thumbnail[:14] + "hqdefault.jpg")
        embed.set_footer(text=embed_footer)

        if not vc.is_playing():
            await vc.play(song)

        else:
            vc.queue.put(song)
            embed.fields[0].name = "Added to Queue"

        embed.add_field(name="Position in Queue", value=f"{vc.queue.count}", inline=True)
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
    async def filter(self, ctx,
                     filter_: discord.Option(choices=[
                         discord.OptionChoice(name="Clear", value="clear"),
                         discord.OptionChoice("BaseBoost", value="BaseFilter"),
                         discord.OptionChoice("Karaoke", value="Karaoke"),
                         discord.OptionChoice("Timescale", value="Timescale"),
                         discord.OptionChoice("Tremolo", value="Tremolo"),
                         discord.OptionChoice("Vibrato", value="Vibrato"),
                         discord.OptionChoice("Rotation", value="Rotation"),
                         discord.OptionChoice("Distortion", value="Distortion"),
                         discord.OptionChoice("ChannelMix", value="ChannelMix"),
                         discord.OptionChoice("LowPass", value="LowPass")
                     ])
                     ):
        vc = ctx.voice_client

        if not vc:
            return await ctx.respond("I am not connected to a voice channel.")

        if not vc.is_playing():
            return await ctx.respond("I am not playing anything.")

        match filter_:
            case "clear":
                await vc.set_filter(None)
                await ctx.respond("Cleared the filter.")
            case "BaseFilter":
                await vc.set_filter(wavelink.filters.BaseFilter())
            case "Karaoke":
                await vc.set_filter(wavelink.filters.Karaoke())
            case "Timescale":
                await vc.set_filter(wavelink.filters.Timescale())
            case "Tremolo":
                await vc.set_filter(wavelink.filters.Tremolo())
            case "Vibrato":
                await vc.set_filter(wavelink.filters.Vibrato())
            case "Rotation":
                await vc.set_filter(wavelink.filters.Rotation())
            case "Distortion":
                await vc.set_filter(wavelink.filters.Distortion())
            case "ChannelMix":
                await vc.set_filter(wavelink.filters.ChannelMix())
            case "LowPass":
                await vc.set_filter(wavelink.filters.LowPass())


def setup(client):
    client.add_cog(Main(client))
