try:
    import discord, json, sqlite3, configparser, logging
    from discord.ext import commands
except Exception as errr:
    print("Unable to import modules. Please make sure you have the required modules installed. Error: ", errr)
    exit()


intents = discord.Intents.all()

# Loading config.ini
config = configparser.ConfigParser()

try:
   config.read('data/config.ini')
except Exception as e:
    print("Error reading the config.ini file. Error: " + str(e))
    exit()



#  ==Getting variables from config file==
try:
    prefix: str = config.get('general', 'prefix')
    log_level: str = config.get('general', 'log_level')
    presence: str = config.get('general', 'presence')


    embed_footer: str = config.get('discord', 'embed_footer')
    embed_header: str = config.get('discord', 'embed_header')
    embed_color: int = int(config.get('discord', 'embed_color'), base=16)
    embed_icon: str = config.get('discord', 'embed_icon')
    embed_url: str = config.get('discord', 'embed_url')

    bot_token: str = config.get('secret', 'discord_token')

    music_save: str = config.get('emoji', 'music_save')
    music_loop: str = config.get('emoji', 'music_loop')
    music_pause: str = config.get('emoji', 'music_pause')
    music_stop: str = config.get('emoji', 'music_stop')
    music_skip: str = config.get('emoji', 'music_skip')
    music_vol_down: str = config.get('emoji', 'music_vol_down')
    music_vol_up: str = config.get('emoji', 'music_vol_up')


except Exception as err:
    print("Error getting variables from the config file. Error: " + str(err))
    exit(1)


# Initializing the logger
def colorlogger(name='moonball'):
    from colorlog import ColoredFormatter
    # disabler loggers
    for logger in logging.Logger.manager.loggerDict:
        logging.getLogger(logger).disabled = True
    logger = logging.getLogger(name)
    stream = logging.StreamHandler()
    LogFormat = "%(reset)s%(log_color)s%(levelname)-8s%(reset)s | %(log_color)s%(message)s"
    stream.setFormatter(ColoredFormatter(LogFormat))
    logger.addHandler(stream)
    # Set logger level
    if log_level.upper() in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        logger.setLevel(log_level.upper())
    else:
        log.warning(f"Invalid log level {log_level}. Defaulting to INFO.")
        logger.setLevel("INFO")
    return logger # Return the logger

log = colorlogger()

try:
    con = sqlite3.connect('./data/data.db')
except Exception as err:
    log.error("Error: Could not connect to data.db." + str(err))
    exit(1)
# noinspection PyUnboundLocalVariable
cur = con.cursor()


# noinspection PyUnboundLocalVariable
client = commands.Bot(command_prefix=prefix, intents=intents, help_command=None, case_insensitive=True)  # Setting prefix


async def input_sanitizer(input_str):
    # Sanitize input
    cleaned = input_str.replace("'", "").replace('"', "").replace("`", "").replace("\\", "").replace("\n", "").replace("\r", "").replace(";", '')
    return cleaned

music_channel = 880368661557309443