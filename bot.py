import asyncio
import os
import sys
from backend import client, bot_token, log
import discord.utils


@client.event
async def on_ready():
    print("Connected to Discord!")
    log.info(f"Bot is ready. Logged in as {client.user}")


async def load_cogs():
    for file in os.listdir('./cogs'):
        if file.endswith('.py'):
            await client.load_extension(f'cogs.{file[:-3]}')


asyncio.run(load_cogs())


# make a command to sync slash cmds

@client.command()
async def sync(ctx):
    fmt = await ctx.client.tree.sync()
    await ctx.send("Done")


try:
    client.run(bot_token)
except discord.LoginFailure:
    log.critical("Invalid Discord Token. Please check your config file.")
    sys.exit()
