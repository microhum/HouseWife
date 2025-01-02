from typing import cast
import discord
from discord.ext import commands
import wavelink
import aiohttp
import lyricsgenius
from client import Bot

class Music(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.genius = bot.genius

    @commands.command(aliases=["p"])
    async def play(self, ctx: discord.ApplicationContext, *, query: str) -> None:
        """Play a song with the given query."""
        if not ctx.guild:
            return

        player: wavelink.Player
        player = cast(wavelink.Player, ctx.voice_client)  # type: ignore

        if not player:
            try:
                player = await ctx.author.voice.channel.connect(cls=wavelink.Player)  # type: ignore
            except AttributeError:
                await ctx.send("Please join a voice channel first before using this command.")
                return
            except discord.ClientException:
                await ctx.send("I was unable to join this voice channel. Please try again.")
                return

        player.autoplay = wavelink.AutoPlayMode.enabled

        if not hasattr(player, "home"):
            player.home = ctx.channel
        elif player.home != ctx.channel:
            await ctx.send(f"You can only play songs in {player.home.mention}, as the player has already started there.")
            return

        tracks: wavelink.Search = await wavelink.Playable.search(query, source=wavelink.TrackSource.SoundCloud)
        if not tracks:
            await ctx.send(f"{ctx.author.mention} - Could not find any tracks with that query. Please try again.")
            return

        if isinstance(tracks, wavelink.Playlist):
            added: int = await player.queue.put_wait(tracks)
            await ctx.send(f"Added the playlist **`{tracks.name}`** ({added} songs) to the queue.")
        else:
            track: wavelink.Playable = tracks[0]
            await player.queue.put_wait(track)
            await ctx.send(f"Added **`{track}`** to the queue.")

        if not player.playing:
            await player.play(player.queue.get(), volume=30)

        try:
            await ctx.message.delete()
        except discord.HTTPException:
            pass

    @commands.command(aliases=["s"])
    async def skip(self, ctx: discord.ApplicationContext) -> None:
        """Skip the current song."""
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        if not player:
            return

        await player.skip(force=True)
        await ctx.message.add_reaction("❤️")

    @commands.command(aliases=["f"])
    async def filter(self, ctx: discord.ApplicationContext, mode: str) -> None:
        """Set the filter to a specified style."""
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        if not player:
            return

        filters: wavelink.Filters = player.filters

        if mode.lower() == "nightcore":
            filters.timescale.set(pitch=1.2, speed=1.2, rate=1)
        elif mode.lower() == "sigma":
            filters.timescale.set(pitch=0.8, speed=0.8, rate=1)
        elif mode.lower() == "normal":
            filters.timescale.set(pitch=1.0, speed=1.0, rate=1)
        else:
            await ctx.send("Invalid mode. Please choose from 'nightcore', 'sigma', or 'normal'.")
            return

        await player.set_filters(filters)
        await ctx.message.add_reaction("❤️")

    @commands.command(name="toggle", aliases=["pause", "resume", "t"])
    async def pause_resume(self, ctx: discord.ApplicationContext) -> None:
        """Pause or Resume the Player depending on its current state."""
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        if not player:
            return

        await player.pause(not player.paused)
        await ctx.message.add_reaction("❤️")

    @commands.command(aliases=["v"])
    async def volume(self, ctx: discord.ApplicationContext, value: int) -> None:
        """Change the volume of the player."""
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        if not player:
            return

        if value < 0 or value > 100:
            await ctx.send("Volume must be between 0 and 100.")
            return

        await player.set_volume(value)
        await ctx.message.add_reaction("❤️")

    @commands.command(aliases=["dc", "leave", "stop"])
    async def disconnect(self, ctx: discord.ApplicationContext) -> None:
        """Disconnect the Player."""
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        if not player:
            return

        await player.disconnect()
        await ctx.message.add_reaction("❤️")

    @commands.command(aliases=["q"])
    async def queue(self, ctx: discord.ApplicationContext) -> None:
        """Display the current queue."""
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        if not player or not player.queue:
            await ctx.send("The queue is currently empty.")
            return

        embed = discord.Embed(title="Current Queue")
        for i, track in enumerate(player.queue, start=1):
            embed.add_field(name=f"{i}. {track.title}", value=f"by {track.author}", inline=False)

        await ctx.send(embed=embed)

    @commands.command(aliases=["lyrics"])
    async def show_lyrics(self, ctx: discord.ApplicationContext, *, song_title: str) -> None:
        """Show the lyrics of the current song."""

        try:
            await ctx.send(f"Searching for lyrics of {song_title}...")
            song = self.genius.search_song(song_title)
            if song:
                embed = discord.Embed(title=f"Lyrics for {song.title} by {song.artist}", description=song.lyrics[:4096])
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"Could not find lyrics for {song_title}.")
        except Exception as e:
            await ctx.send(f"An error occurred while fetching lyrics: {e}")
    
    # @commands.command(aliases=["h"])
    # async def help(self, ctx: discord.ApplicationContext) -> None:
    #     """Display help information."""
    #     embed = discord.Embed(title="Help", description="List of available commands:")
    #     embed.add_field(name="play <query>", value="Play a song with the given query.", inline=False)
    #     embed.add_field(name="skip", value="Skip the current song.", inline=False)
    #     embed.add_field(name="filter <mode>", value="Set the filter to a specified style (nightcore, sigma, normal).", inline=False)
    #     embed.add_field(name="toggle", value="Pause or Resume the Player depending on its current state.", inline=False)
    #     embed.add_field(name="volume <value>", value="Change the volume of the player (0-100).", inline=False)
    #     embed.add_field(name="disconnect", value="Disconnect the Player.", inline=False)
    #     embed.add_field(name="queue", value="Display the current queue.", inline=False)

    #     await ctx.send(embed=embed)