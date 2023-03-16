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
        log.info(f"{node.id} is ready.")  # print a message

    @commands.Cog.listener()
    async def on_ready(self):
        log.info("Cog: Listeners.py Loaded")

        self.get_member_count.start()

        while not self.member_count > -1:
            await asyncio.sleep(1)

        log.info(f"I am in {len(self.client.guilds)} guilds. They have {self.member_count} members.")
        self.random_status.start()

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEventPayload):
        if payload.reason == "FINISHED":
            try:
                await payload.player.play(payload.player.queue.get()) #, payload_args={"skipSegments": ["music_offtopic"]}
            except wavelink.QueueEmpty:
                log.debug("Queue is empty, disconnecting.")
                await payload.player.disconnect()
        # possible reasons: FINISHED, LOAD_FAILED, STOPPED, REPLACED, CLEANUP
        # load_failed = track failed to load
        # stopped = track was stopped
        # replaced = track was replaced
        # cleanup = player was destroyed

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):  # TODO test
        log.debug(f"Voice state update: {member} {before} {after}")

        if member == self.client.user:
            return

        # if a channel disconnect/connect was encountered, return
        if after.channel is None or before.channel is None:
            return

        # disconnect if member leaves the voice channel and the bot is alone
        if len(after.channel.members) == 1 and self.client.user in after.channel.members:
            await member.guild.voice_client.disconnect()

        guild = after.channel.guild

        # if the bot is not connected to a voice channel, return
        if not guild.voice_client:
            return

        # if the bot is not in the same voice channel as the user, return
        if member.voice.channel != guild.voice_client.channel:
            if len(before.channel.members) == 1 and len(after.channel.members) == 1 and after.channel != before.channel:
                await member.guild.voice_client.moveto(after.channel.id)
            return

        if len(after.channel.members) == 2 and before.self_deaf != after.self_deaf:
            await member.guild.voice_client.set_pause(not after.self_deaf)

    @commands.Cog.listener()
    async def on_application_command(self, ctx: discord.ApplicationContext):
        log.info(f"Command `/{ctx.command.qualified_name}` was used by `{ctx.author}` in `{ctx.guild}`")

    @commands.Cog.listener()
    async def on_application_command_error(self, ctx: discord.ApplicationContext, error: Exception):
        if isinstance(error, commands.NoPrivateMessage):
            await ctx.respond("This command cannot be used in a DM.")
        else:
            if raise_errors:
                raise error

        log.error(f"Command {ctx.command.name} failed with error: {error}")

    @tasks.loop(seconds=60 * 60)
    async def random_status(self):
        activities = (
            f"{self.member_count} Users!",
            f"{len(self.client.guilds)} Guilds!",
            "/play",
        )

        types = (
            discord.ActivityType.watching,
            discord.ActivityType.watching,
            discord.ActivityType.playing,
        )

        rand_int = random.randint(0, len(activities) - 1)

        try:
            await self.client.change_presence(
                activity=discord.Activity(type=types[rand_int], name=activities[rand_int]))
        except Exception as e:
            log.warning(f"Error in changing status : {e}")
        log.debug(f"Changed status to {activities[rand_int]}")

    @tasks.loop(seconds=3600 * 24)  # Run every 24 hours
    async def get_member_count(self):
        _member_count = 0

        for guild in self.client.guilds:
            guild = await self.client.fetch_guild(guild.id, with_counts=True)
            _member_count += guild.approximate_member_count

        self.member_count = _member_count
        log.debug(f"[Listeners] | Member Count: {self.member_count}")


def setup(client):
    client.add_cog(Listeners(client))
