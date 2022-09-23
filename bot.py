import os
from backend import client, bot_token, log

@client.event
async def on_ready():
    print("Connected to Discord!")
    log.info(f"Bot is ready. Logged in as {client.user}")


for file in os.listdir('./cogs'):
    if file.endswith('.py'):
        client.load_extension(f'cogs.{file[:-3]}')

client.run(bot_token)