import datetime
import discord
from discord.ext import commands
import wavelink
from backend import wavelink_host, wavelink_password, wavelink_port, embed_footer, log


class Main(discord.Cog):
    def __init__(self, client):
        self.client = client

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
            return await ctx.respond("Streams are not supported.")

        if song.duration > 600:
            return await ctx.respond("Songs longer than 10 minutes are not supported.")

        duration = datetime.timedelta(seconds=song.duration)

        embed = discord.Embed(title="Music")
        embed.add_field(name="Now Playing", value=f"[{song.title}]({song.uri})")
        embed.add_field(name="Duration", value=f"{str(duration)[2:]}", inline=False)
        embed.set_image(url=song.thumbnail)
        embed.set_footer(text=embed_footer)

        if not vc.is_playing():
            await vc.play(song)
            embed.add_field(name="Position in Queue", value=f"1", inline=True)
            await ctx.respond(embed=embed)

        else:
            vc.queue.put(song)

            embed.add_field(name="Position in Queue", value=f"{vc.queue.count + 1}", inline=True)
            embed.fields[0].name = "Added to Queue"

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
            await vc.play(vc.queue.pop(0))
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

        await vc.stop()
        await vc.disconnect()
        vc.queue.clear()

    @commands.slash_command()
    async def volume(self, ctx, volume: int):
        vc = ctx.voice_client

        if not vc:
            return await ctx.respond("I am not connected to a voice channel.")

        if not vc.is_playing():
            return await ctx.respond("I am not playing anything.")

        await vc.set_volume(volume)
        await ctx.respond(f"Set the volume to {volume}.")

    @commands.slash_command()
    async def queue(self, ctx):
        vc = ctx.voice_client

        if not vc:
            return await ctx.respond("I am not connected to a voice channel.")

        if not vc.is_playing():
            return await ctx.respond("I am not playing anything.")

        if vc.queue.count == 0:
            return await ctx.respond("There are no more songs in the queue.")

        embed = discord.Embed(title="Music Queue")
        embed.set_footer(text=embed_footer)

        for i, song in enumerate(vc.queue):
            duration = datetime.timedelta(seconds=song.duration)
            embed.add_field(name=f"{i + 1}. `{song.title}`", value=f"Duration: {str(duration)[2:]}", inline=False)

        await ctx.respond(embed=embed)

    @commands.slash_command(name="resume")
    @commands.slash_command(name="pause")
    async def pauseresume(self, ctx):
        vc = ctx.voice_client

        if not vc:
            return await ctx.respond("I am not connected to a voice channel.")

        if not vc.is_playing():
            return await ctx.respond("I am not playing anything.")

        await vc.set_pause(not vc.paused)
        await ctx.respond("Paused the music.")

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
                         discord.OptionChoice("LowPass", value="LowPass"),
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
