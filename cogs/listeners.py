import discord
import wavelink
from discord.ext import commands
from backend import log


class Listeners(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, node: wavelink.Node):
        log.info(f"{node.identifier} is ready.")  # print a message

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
    client.add_cog(Listeners(client))
