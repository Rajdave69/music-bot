import asyncio
import random
import discord
import wavelink
from discord.ext import commands, tasks
from backend import log, raise_errors


class Listeners(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.member_count = -1

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, node: wavelink.Node):
        log.info(f"{node.identifier} is ready.")  # print a message

    @commands.Cog.listener()
    async def on_ready(self):
        log.info("Cog: Listeners.py Loaded")

        self.get_member_count.start()

        while not self.member_count > -1:
            await asyncio.sleep(1)

        log.info(f"I am in {len(self.client.guilds)} guilds. They have {self.member_count} members.")
        self.random_status.start()

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, player: wavelink.Player, track: wavelink.Track, reason):
        if reason == "FINISHED":
            try:
                await player.play(player.queue.get())
            except wavelink.QueueEmpty:
                log.debug("Queue is empty, disconnecting.")
                await player.disconnect()
        # possible reasons: FINISHED, LOAD_FAILED, STOPPED, REPLACED, CLEANUP
        # load_failed = track failed to load
        # stopped = track was stopped
        # replaced = track was replaced
        # cleanup = player was destroyed

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return
        vc = member.guild.voice_client

        # If the user leaves the VC
        if after.channel is None:

            # And the VC is empty (Except for the bot)
            if len(before.channel.members) == 1:
                await vc.disconnect()

    @commands.Cog.listener()
    async def on_application_command_error(self, ctx: discord.ApplicationContext, error: Exception):
        # if isinstance(error, commands.CommandNotFound):
        #     await ctx.send("Command not found.")
        if isinstance(error, NoVC):
            await ctx.respond("You are not in a voice channel.")
        elif isinstance(error, NotPlaying):
            await ctx.respond("I am not playing anything.")
        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.respond("This command cannot be used in a DM.")

        log.error(f"Command {ctx.command.name} failed with error: {error}")

        if raise_errors:
            raise error


def setup(client):
    client.add_cog(Listeners(client))
