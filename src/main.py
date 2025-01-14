import asyncio
import logging
import os
from discord.ext import commands
from dotenv import load_dotenv
from client import Bot
from music.music import Music
from wsgi import keep_alive

bot: Bot = Bot()

@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError) -> None:
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Command not found. Try saying `w!help`.")
    else:
        await ctx.send("An error occurred. Try saying `w!help`.")
        logging.error("An error occurred: %s", error)

async def main() -> None:
    keep_alive()
    async with bot:
        load_dotenv()
        bot.add_cog(Music(bot, GENIUS_TOKEN=os.getenv("GENIUS_TOKEN")))
        await bot.start(token=os.getenv("DISCORD_TOKEN"))

       
asyncio.run(main())