import configparser
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
    raise_errors: bool = config.getboolean('general', 'raise_errors')
    owner_ids: list = config.get('general', 'owner_ids').strip().split(',')
    owner_guilds: list = config.get('general', 'owner_guilds').strip().split(',')

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
    # get the current textbox (discord option)'s value
    current_val = ctx.interaction.data['options'][0]['value'].lower()
    print(current_val)

    async with aiosqlite.connect('data/data.db') as db:
        if current_val:

            # If it is a number, then it is a playlist id
            if current_val[0].isdigit():
                # select id from public playlist where id starts with current_val
                async with db.execute("SELECT id, name FROM playlists WHERE id LIKE ? AND visibility = '1'",
                                      (current_val + '%',)) as cursor:
                    playlists = await cursor.fetchall()
                    print(playlists)
                    if playlists:
                        return list({f"{x[0]} | {x[1]}" for x in playlists})

            # If it is a letter, then it is a playlist name
            else:
                async with db.execute("SELECT name FROM playlists WHERE author = ? AND  name LIKE ?",
                                      (ctx.interaction.user.id, current_val + '%')) as cursor:
                    playlists = await cursor.fetchall()
                    if playlists:
                        return list({x[0] for x in playlists})

            return []

        async with db.execute("SELECT name FROM playlists WHERE author = ?", (ctx.interaction.user.id,)) as cursor:
            playlists = await cursor.fetchall()

            if not playlists:
                return []

        return list({x[0] for x in playlists}) if playlists else []


def is_owner(ctx: commands.Context) -> bool:
    return str(ctx.author.id) in owner_ids


async def vc_exists(ctx) -> bool:
    if ctx.guild is None:  # todo check if the ctx.author is in the vc too
        raise commands.NoPrivateMessage

    if not ctx.voice_client:
        await ctx.respond(embed=error_template("I am not connected to a voice channel or playing anything."))

    elif not ctx.voice_client.is_playing():
        await ctx.respond(embed=error_template("I am not playing anything."))

    return True


async def playlist_exists(ctx, playlist_name) -> bool:
    async with aiosqlite.connect('data/data.db') as db:
        async with db.execute("SELECT name FROM playlists WHERE author = ? AND name = ?",
                              (ctx.interaction.user.id, playlist_name)) as cursor:
            playlist = await cursor.fetchone()

            if not playlist:
                await ctx.respond(embed=error_template(f"Playlist `{playlist_name}` does not exist."))
                return False

    return True


_embed_template = discord.Embed(title="Music", color=embed_color, url=embed_url)
_embed_template.set_footer(text=embed_footer, icon_url=embed_icon)

error_template = discord.Embed(title="Error", color=discord.Color.red(), url=embed_url)
error_template.set_footer(text=embed_footer, icon_url=embed_icon)

embed_template = lambda: _embed_template.copy()


def error_template(description: str) -> discord.Embed:
    _error_template = discord.Embed(
        description=description,
        color=0xff0000,
        url=embed_url
    )
    _error_template.set_footer(text=embed_footer)

    return _error_template.copy()
