import sqlite3
import discord
from discord.ext import commands
from backend import log, embed_footer, embed_color, embed_url, is_owner


class Owners(commands.Cog):
    def __init__(self, client):
        self.client = client

    owners = discord.SlashCommandGroup("owners", "Owner commands")

    @owners.command()
    async def reload(self, ctx, cog):
        if not is_owner(ctx):
            await ctx.respond("You are not the bot owner.")
            return

        try:
            self.client.reload_extension(f"cogs.{cog}")
            await ctx.respond(f"Reloaded {cog}.")
        except Exception as e:
            await ctx.respond(f"Failed to reload {cog}.\n{e}")

    @owners.command()
    async def load(self, ctx, cog):
        if not is_owner(ctx):
            await ctx.respond("You are not the bot owner.")
            return

        try:
            self.client.load_extension(f"cogs.{cog}")
            await ctx.respond(f"Loaded {cog}.")
        except Exception as e:
            await ctx.respond(f"Failed to load {cog}.\n{e}")

    @owners.command()
    async def exec_sql(self, ctx, sql: str):
        if not is_owner(ctx):
            await ctx.respond("You are not the bot owner.")
            return

        con = sqlite3.connect("./data/data.db")
        cur = con.cursor()

        try:
            cur.execute(sql)
            res = cur.fetchall()
            con.commit()

            embed = discord.Embed(title="SQL", description=f"Executed SQL query.",
                                  url=embed_url, color=embed_color)
            for row in res:
                embed.add_field(name=row, value="‎", inline=False)
            embed.set_footer(text=embed_footer)
            await ctx.respond(embed=embed)

        except Exception as e:
            await ctx.respond(f"Failed to execute SQL.\n{e}")


def setup(client):
    client.add_cog(Owners(client))
