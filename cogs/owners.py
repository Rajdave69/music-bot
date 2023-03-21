import sqlite3
import discord
from discord import app_commands
from discord.ext import commands
from backend import log, embed_footer, embed_color, embed_url, is_owner, owner_guilds, error_template


class Owners(commands.GroupCog, name="owners", guild_ids=owner_guilds):
    def __init__(self, client):
        self.client = client

    # owners = discord.SlashCommandGroup("owners", "Owner commands", guild_ids=owner_guilds)

    @commands.Cog.listener()
    async def on_ready(self):
        log.info("Cog: Owners.py loaded.")

    @app_commands.command()
    async def reload(self, interaction, cog):
        if not is_owner(interaction):
            await interaction.response.send_message("You are not the bot owner.")
            return

        try:
            self.client.reload_extension(f"cogs.{cog}")
            await interaction.response.send_message(f"Reloaded {cog}.")
        except Exception as e:
            await interaction.response.send_message(f"Failed to reload {cog}.\n{e}")

    @app_commands.command()
    async def load(self, interaction, cog):
        if not is_owner(interaction):
            await interaction.response.send_message("You are not the bot owner.")
            return

        try:
            self.client.load_extension(f"cogs.{cog}")
            await interaction.response.send_message(f"Loaded {cog}.")
        except Exception as e:
            await interaction.response.send_message(f"Failed to load {cog}.\n{e}")

    @app_commands.command()
    async def exec_sql(self, interaction, sql: str):
        if not is_owner(interaction):
            await interaction.response.send_message("You are not the bot owner.")
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
            await interaction.response.send_message(embed=embed)

        except Exception as e:
            await interaction.response.send_message(f"Failed to execute SQL.\n{e}")

    @app_commands.command()
    async def guilds(self, interaction):
        if not is_owner(interaction):
            await interaction.response.send_message("You are not the bot owner.")
            return

        embed = discord.Embed(title="Guilds", description=f"Guilds the bot is in.",
                              url=embed_url, color=embed_color)
        for guild in self.client.guilds:
            embed.add_field(name=guild.name, value=guild.id, inline=False)
        embed.set_footer(text=embed_footer)
        await interaction.response.send_message(embed=embed)

    # create a cog check
    async def cog_check(self, interaction) -> bool:
        if not is_owner(interaction):
            await interaction.response.send_message(embed=error_template("You are not the bot owner."), ephemeral=True)
            return False


def setup(client):
    client.add_cog(Owners(client))
