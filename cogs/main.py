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

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, node: wavelink.Node):
        log.info(f"{node.identifier} is ready.")  # print a message

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

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, player: wavelink.Player, track: wavelink.Track, reason):
        if reason == "FINISHED":
            try:
                await player.play(player.queue.get())
            except wavelink.QueueEmpty:
                await player.disconnect()
        # possible reasons: FINISHED, LOAD_FAILED, STOPPED, REPLACED, CLEANUP
        # load_failed = track failed to load
        # stopped = track was stopped
        # replaced = track was replaced
        # cleanup = player was destroyed

def setup(client):
    client.add_cog(Main(client))
