import asyncio
import logging
import os
from discord.ext import commands
from dotenv import load_dotenv
from client import Bot
from music.music import Music

bot: Bot = Bot()
bot.add_cog(Music(bot, GENIUS_TOKEN=os.getenv("GENIUS_TOKEN")))

@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError) -> None:
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Command not found. Try saying `w!help`.")
    else:
        await ctx.send("An error occurred. Try saying `w!help`.")
        logging.error("An error occurred: %s", error)

async def main() -> None:
    async with bot:
        load_dotenv()
        await bot.start(token=os.getenv("DISCORD_TOKEN"))

       
asyncio.run(main())