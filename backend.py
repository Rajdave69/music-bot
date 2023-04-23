import configparser
import sys
import aiosqlite
import discord
import logging

import discord.app_commands
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

    lavalink_creds = dict(config.items('nodes'))

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

client = commands.Bot(intents=intents, command_prefix="!")  # Creating the Bot


async def get_user_playlists(interaction: discord.Interaction, current) -> list[discord.app_commands.Choice[str]]:
    print(interaction, current)
    # get the current textbox (discord option)'s value
    # current = interaction.data['options'][0]['value'].lower()

    async with aiosqlite.connect('data/data.db') as db:
        if current:
            log.debug(f"Current: {current}")
            # If it is a number, then it is a playlist id
            if current[0].isdigit():
                # select id from public playlist where id starts with current
                async with db.execute("SELECT name, id FROM playlists WHERE id LIKE ? AND visibility = '1'",
                                      (current + '%',)) as cursor:
                    playlists = await cursor.fetchall()
                    log.debug(playlists)
                    if playlists:
                        return list(
                            {discord.app_commands.Choice(name=f"{x[1]} | {x[0]}", value=x[0]) for x in playlists})

            # If it is a letter, then it is a playlist name
            else:
                async with db.execute("SELECT name, id FROM playlists WHERE author = ? AND name LIKE ?",
                                      (interaction.user.id, current + '%')) as cursor:
                    playlists = await cursor.fetchall()
                    log.debug(playlists)
                    if playlists:
                        return list({discord.app_commands.Choice(name=x[0], value=x[0]) for x in playlists})

        async with db.execute("SELECT name, id FROM playlists WHERE author = ?", (interaction.user.id,)) as cursor:
            playlists = await cursor.fetchall()

            log.debug(playlists)
            if not playlists:
                return []

        return [discord.app_commands.Choice(name=x[0], value=x[0]) for x in playlists] \
            if playlists else []


def is_owner(ctx: commands.Context) -> bool:
    return str(ctx.author.id) in owner_ids


async def vc_exists(interaction) -> bool:
    if interaction.guild is None:  # todo check if the ctx.author is in the vc too
        raise commands.NoPrivateMessage

    if not interaction.guild.voice_client:
        await interaction.response.send_message(embed=error_template("I am either not connected to a voice channel or "
                                                                     "not playing anything."), ephemeral=True)

    elif not interaction.guild.voice_client.is_playing():
        await interaction.response.send_message(embed=error_template("I am not playing anything."), ephemeral=True)

    return True


async def playlist_exists(ctx, playlist_name) -> bool:
    async with aiosqlite.connect('data/data.db') as db:
        async with db.execute("SELECT name FROM playlists WHERE author = ? AND name = ?",
                              (ctx.interaction.user.id, playlist_name)) as cursor:
            playlist = await cursor.fetchone()

            if not playlist:
                await ctx.respond(embed=error_template(f"Playlist `{playlist_name}` does not exist."), ephemeral=True)
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


async def increment_listens(playlist_id):
    async with aiosqlite.connect('data/data.db') as db:
        async with db.execute("UPDATE playlists SET listens = listens + 1 WHERE id = ?", (playlist_id,)):
            await db.commit()
