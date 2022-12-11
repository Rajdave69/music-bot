import configparser
import sqlite3
import sys
import aiosqlite
import discord
import logging
from discord.ext import commands

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


client = commands.Bot(intents=intents)  # Setting prefix


async def get_user_playlists(ctx: discord.AutocompleteContext) -> list[str or None]:
    con = sqlite3.connect('data/data.db')
    cur = con.cursor()
    cur.execute("SELECT name FROM playlists WHERE author = ?", (ctx.interaction.user.id,))
    res = cur.fetchall()
    return list({x[0] for x in res}) if res else []
