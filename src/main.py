import discord
import os
from dotenv import load_dotenv
from discord.ext import commands
import wavelink

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def connect_nodes(self):
        """Connect to our Lavalink nodes."""
        await self.bot.wait_until_ready()

        await wavelink.Pool.create_node(
            bot=self.bot, host="0.0.0.0", port=2333, password="youshallnotpass"
        )

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, node: wavelink.Node):
        """Event fired when a node has finished connecting."""
        print(f"Node: <{node.identifier}> is ready!")

    @commands.command()
    async def join(self, ctx):
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            player = self.bot.wavelink.get_player(ctx.guild.id, cls=wavelink.Player)
            await player.connect(channel.id)
            await ctx.send(f"Joined {channel}")
        else:
            await ctx.send("You are not in a voice channel!")
    
    @commands.command()
    async def leave(self, ctx):
        player = self.bot.wavelink.get_player(ctx.guild.id)
        if player.is_connected:
            await player.disconnect()
            await ctx.send("Disconnected from the voice channel")
        else:
            await ctx.send("I am not in a voice channel!")

    @commands.command()
    async def play(self, ctx, *, query: str):
        player = self.bot.wavelink.get_player(ctx.guild.id)
        if not player.is_connected:
            await ctx.send("I am not connected to a voice channel!")
            return

        tracks = await wavelink.YouTubeTrack.search(query=query)
        if not tracks:
            await ctx.send("No tracks found!")
            return

        await player.play(tracks[0])
        await ctx.send(f"Now playing: {tracks[0].title}")


load_dotenv()

async def setup(bot):
    # Add cog and connect Lavalink nodes
    await bot.add_cog(Basic(bot))
    await bot.add_cog(Music(bot))
    cog = bot.get_cog("Music")
    await cog.connect_nodes()

class BotClient(commands.Bot):
    async def setup_hook(self):
        await setup(self)

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print("------")

class Basic(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def hello(self, ctx, name: str = None):
        name = name or ctx.author.name
        await ctx.send(f"Hello ja {name}!")

    @commands.command(name="Say Hello")
    async def hi(self, ctx, user):
        await ctx.send(f"{ctx.author.mention} says hello to {user.name}!")

intents = discord.Intents.default()
intents.message_content = True

bot = BotClient(
    command_prefix=commands.when_mentioned_or("!"),
    description="Relatively simple music bot example",
    intents=intents,
)

token = os.getenv("DISCORD_TOKEN")
bot.run(token)
