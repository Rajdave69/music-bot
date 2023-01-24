from discord.ext import commands
import discord
import wavelink


class Filters(commands.Cog):  # TODO: Add more filters
    def __init__(self, client):
        self.client = client

    filters = discord.SlashCommandGroup("filter", "Filter commands")

    @filters.command()
    async def vibrato(self, ctx, frequency: float = 2.0, depth: float = 0.5):
        """Apply a vibrato filter."""

        # check if the input is valid
        if not 0.0 < frequency < 14.0:
            return await ctx.respond("Frequency must be between 0.0 and 14.0")
        if not 0.0 < depth < 1.0:
            return await ctx.respond("Depth must be between 0.0 and 1.0")

        vc = ctx.voice_client
        await vc.set_filter(wavelink.filters.Filter(vibrato=wavelink.filters.Vibrato(frequency=frequency, depth=depth)))

        await ctx.respond("Vibrato filter has been applied.")

    @filters.command()
    async def karaoke(self, ctx, level: float = 1.0, mono_level: float = 1.0,
                      filter_band: float = 220.0, filter_width: float = 100.0):
        """Apply a karaoke filter."""

        # check if the input is valid
        if not 0.0 < level <= 1.0:
            return await ctx.respond("Level must be between 0.0 and 1.0")
        if not 0.0 < mono_level <= 1.0:
            return await ctx.respond("Mono Level must be between 0.0 and 1.0")
        if not 0.0 < filter_band <= 22000.0:
            return await ctx.respond("Filter Band must be between 0.0 and 22000.0")
        if not 0.0 < filter_width <= 100.0:
            return await ctx.respond("Filter Width must be between 0.0 and 100.0")

        vc = ctx.voice_client
        await vc.set_filter(wavelink.filters.Filter(
            karaoke=wavelink.filters.Karaoke(level=level, mono_level=mono_level, filter_band=filter_band,
                                             filter_width=filter_width)))
        await ctx.respond("Karaoke filter has been applied.")

    @filters.command()
    async def timescale(self, ctx, speed: float = 1.0, pitch: float = 1.0, rate: float = 1.0):
        """Apply a timescale filter."""

        # check if the input is valid
        if not 0.0 < speed < 2.0:
            return await ctx.respond("Speed must be between 0.0 and 2.0")
        if not 0.0 < pitch < 2.0:
            return await ctx.respond("Pitch must be between 0.0 and 2.0")

        vc = ctx.voice_client
        await vc.set_filter(
            wavelink.filters.Filter(timescale=wavelink.filters.Timescale(speed=speed, pitch=pitch, rate=rate)))
        await ctx.respond("Timescale filter has been applied.")

    @filters.command()
    async def filter_reset(self, ctx):
        """Resets the filter."""
        vc = ctx.voice_client
        await vc.set_filter(wavelink.filters.Filter())
        await ctx.respond("Reset filters.")


def setup(client):
    client.add_cog(Filters(client))
