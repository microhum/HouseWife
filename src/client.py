import logging
import os
import discord
from discord.ext import commands
import wavelink

class Bot(commands.Bot):
    def __init__(self) -> None:
        # Intents setup
        intents: discord.Intents = discord.Intents.default()
        intents.message_content = True
        
        # Ensure log directory exists
        os.makedirs("log", exist_ok=True)
        
        # Logging setup
        logging.basicConfig(filename="log/bot.log", level=logging.INFO, filemode="a", format="%(asctime)s:%(levelname)s:%(name)s: %(message)s")
        logging.getLogger().addHandler(logging.StreamHandler())
        
        super().__init__(command_prefix="w!", intents=intents)
    
    async def on_ready(self) -> None:

        # Edit Bot Profile Picture
        await self.user.edit(avatar=open("images/default_profile_resize.gif", "rb").read())
        logging.info("Logged in: %s | %s", self.user, self.user.id)
        
        # Wavelink setup
        host = os.getenv("LAVALINK_HOST", "localhost")
        port = os.getenv("LAVALINK_PORT", "2333")
        password = os.getenv("LAVALINK_PASSWORD", "youshallnotpass")
        nodes = [wavelink.Node(uri=f'http://{host}:{port}', password=password)]

        await wavelink.Pool.connect(nodes=nodes, client=self)
        await self.wait_until_ready()