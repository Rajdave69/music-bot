import datetime
import discord
from discord.ext import commands
import wavelink
from backend import wavelink_host, wavelink_password, wavelink_port, embed_footer, log


class Main(discord.Cog):
    def __init__(self, client):
        self.client = client
        self.queue = {}

    @commands.Cog.listener()
    async def on_ready(self):
        print("Connected to Discord!")
        await self.connect_nodes()

    async def connect_nodes(self):
        await self.client.wait_until_ready()
        await wavelink.NodePool.create_node(
            bot=self.client,
            host=wavelink_host,
            port=wavelink_port,
            password=wavelink_password
        )

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, node: wavelink.Node):
        log.info(f"{node.identifier} is ready.")  # print a message

def setup(client):
    client.add_cog(Main(client))
