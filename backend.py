import configparser
import sys
import aiosqlite
import discord
import logging
from discord.ext import commands
import copy

intents = discord.Intents.default()

# Loading config.ini
config = configparser.ConfigParser()

try:
    config.read('data/config.ini')
except Exception as e:
    print("Error reading the config.ini file. Error: " + str(e))
    sys.exit()

#  Getting variables from config.ini
try:
    log_level: str = config.get('general', 'log_level')
    presence: str = config.get('general', 'presence')
    raise_errors: bool = config.getboolean('general', 'raise_errors')
    owner_ids: list = config.get('general', 'owner_ids').strip().split(',')

    embed_footer: str = config.get('discord', 'embed_footer')
    embed_header: str = config.get('discord', 'embed_header')
    embed_color: int = int(config.get('discord', 'embed_color'), base=16)
    embed_icon: str = config.get('discord', 'embed_icon')
    embed_url: str = config.get('discord', 'embed_url')

    bot_token: str = config.get('secret', 'discord_token')

    wavelink_host: str = config.get('wavelink', 'host')
    wavelink_port: int = int(config.get('wavelink', 'port'))
    wavelink_password: str = config.get('wavelink', 'password')

except Exception as err:
    print("Error getting variables from the config file. Error: " + str(err))
    sys.exit()


# Initializing the logger
def colorlogger(name='music-bot'):
    from colorlog import ColoredFormatter
    logger = logging.getLogger(name)
    stream = logging.StreamHandler()
    stream.setFormatter(ColoredFormatter("%(reset)s%(log_color)s%(levelname)-8s%(reset)s | %(log_color)s%(message)s"))
    logger.addHandler(stream)
    # Set logger level
    if log_level.upper() in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        logger.setLevel(log_level.upper())
    else:
        log.warning(f"Invalid log level {log_level}. Defaulting to INFO.")
        logger.setLevel("INFO")
    return logger  # Return the logger


log = colorlogger()

client = commands.Bot(intents=intents)  # Creating the Bot


async def get_user_playlists(ctx: discord.AutocompleteContext) -> list[str or None]:
    async with aiosqlite.connect('data/data.db') as db:
        async with db.execute("SELECT name FROM playlists WHERE author = ?", (ctx.interaction.user.id,)) as cursor:
            playlists = await cursor.fetchall()

            if not playlists:
                return []

            return list({x[0] for x in playlists}) if playlists else []


def is_owner(ctx: commands.Context) -> bool:
    return str(ctx.author.id) in owner_ids


async def vc_exists(ctx):
    if ctx.guild is None:
        raise commands.NoPrivateMessage

    if not ctx.voice_client:
        embed = error_template.copy()
        embed.description = "I am not connected to a voice channel or playing anything."
        await ctx.respond(embed=embed)

    elif not ctx.voice_client.is_playing():
        embed = error_template.copy()
        embed.description = "I am not playing anything."
        await ctx.respond(embed=embed)


embed_template = discord.Embed(title="Music", color=embed_color, url=embed_url)
embed_template.set_footer(text=embed_footer, icon_url=embed_icon)

error_template = discord.Embed(title="Error", color=discord.Color.red(), url=embed_url)
error_template.set_footer(text=embed_footer, icon_url=embed_icon)
