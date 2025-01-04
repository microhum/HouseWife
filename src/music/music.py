import asyncio
import logging
import random
from typing import cast
import discord
from discord.ext import commands
import lyricsgenius
import wavelink
from wavelink.types.tracks import TrackPayload
from client import Bot
from utils.format import *
import os

class Music(commands.Cog):
    def __init__(self, bot: Bot, GENIUS_TOKEN: str) -> None:
        self.bot: Bot = bot
        self.genius = lyricsgenius.Genius(GENIUS_TOKEN)
        wavelink.Player.inactive_timeout = 5

    async def play_random_sound(self, player: wavelink.Player, category: str) -> None:
        try:
            category_map = {
                "inactive": 
                {
                    "sleepy": "https://soundcloud.com/vermil-1554451/sleepy", 
                    "music_taste": "https://soundcloud.com/vermil-1554451/elevenlabs_2025-01",
                    "soquiet": "https://soundcloud.com/vermil-1554451/soqueit",
                    "songrunningout": "https://soundcloud.com/vermil-1554451/songrun",
                    "sawadeeka": "https://soundcloud.com/vermil-1554451/sawadeeka"
                 },
            }

            sounds = category_map.get(category, None)
            if sounds is None:
                logging.error(f"Category {category} does not exist in the category map.")
                return

            sound_link = random.choice(list(sounds.values()))
            tracks = await wavelink.Playable.search(sound_link)

            if not tracks:
                logging.error("No tracks found for the given YouTube link.")
                return

            track = tracks[0]
            await player.queue.put_wait(track)

        except Exception as e:
            logging.error(f"Failed to play sound: {e}")

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload) -> None:
        logging.info("Wavelink Node connected: %r | Resumed: %s", payload.node, payload.resumed)

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload) -> None:
        player: wavelink.Player | None = payload.player
        if not player:
            # Handle edge cases...
            return

        original: wavelink.Playable | None = payload.original
        track: wavelink.Playable = payload.track

        total_length = format_duration(sum(_track.length for _track in player.queue._items) + track.length)
        embed: discord.Embed = discord.Embed(title="Now Playing", color=discord.Color.green())
        embed.description = (f"**{track.title}** by `{track.author}`\n"
                             f"Song Duration: **`{format_duration(track.length)}`**\n"
                             f"Songs in the queue: **`{len(player.queue)}`**\n"
                             f"Total Duration: **`{total_length}`**")

        # if track.artwork:
        #     embed.set_image(url=track.artwork)

        if original and original.recommended:
            embed.description += f"\n\n`This track was recommended via {track.source}`"

        if track.album.name:
            embed.add_field(name="Album", value=track.album.name)

        await player.home.send(embed=embed)

    # Handle inactive player with random sound
    @commands.Cog.listener()
    async def on_wavelink_inactive_player(self, player: wavelink.Player) -> None:
        await self.play_random_sound(player, "inactive")
    
    # @commands.Cog.listener()
    # async def on_wavelink_track_end(self, payload: wavelink.TrackStartEventPayload) -> None:
    #     player: wavelink.Player | None = payload.player
    #     while not player.queue:
    #         await self.play_random_sound(player.home, "inactive")
    #         await asyncio.sleep(60)

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
                await self.play_random_sound(player, "inactive")

            except AttributeError:
                await ctx.send("Please join a voice channel first before using this command.")
                return
            except discord.ClientException:
                await ctx.send("I was unable to join this voice channel. Please try again.")
                return

        player.autoplay = wavelink.AutoPlayMode.partial

        if not hasattr(player, "home"):
            player.home = ctx.channel
        elif player.home != ctx.channel:
            await ctx.send(f"You can only play songs in {player.home.mention}, as the player has already started there.")
            return
        
        if "youtube.com" in query or "youtu.be" in query:
            tracks: wavelink.Search = await wavelink.Playable.search(query)
        elif "soundcloud.com" in query:
            tracks: wavelink.Search = await wavelink.Playable.search(query)
        elif "spotify.com" in query:
            tracks: wavelink.Search = await wavelink.Playable.search(query)
        else:
            tracks: wavelink.Search = await wavelink.Playable.search(query, source=wavelink.TrackSource.YouTubeMusic)
        
        if not tracks:
            await ctx.send(f"{ctx.author.mention} - Could not find any tracks with that query. Please try again.")
            return
        
        # Handle max queue duration
        total_length = sum(track.length for track in player.queue._items)
        if total_length + tracks[0].length > 7200000:  # 2 hours in milliseconds
            await ctx.send(f"{ctx.author.mention} - Adding this track would exceed the maximum queue duration of 2 hours.")
            return
        
        
        if isinstance(tracks, wavelink.Playlist):
            added: int = await player.queue.put_wait(tracks)
            tracks_length = format_duration(sum(_track.length for _track in tracks))
            embed = discord.Embed(color=discord.Color.green())
            embed.description = (f"Added the playlist **`{tracks.name}`** ({added} songs) to the queue.\n"
                                 f"Playlist Duration: **`{tracks_length}`**")
            await ctx.send(embed=embed)
        else:
            track: wavelink.Playable = tracks[0]
            await player.queue.put_wait(track)
            embed = discord.Embed(color=discord.Color.green())
            embed.description = (f"Added **`{track}`** to the queue.\n"
                                 f"Duration: **`{format_duration(track.length)}`**")
            await ctx.send(embed=embed)

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

        if player.playing:
            current_track = player.current
            embed.add_field(name="Now Playing", value=f"**{current_track.title}** by `{current_track.author}` [{format_duration(current_track.length)}]", inline=False)

        total_duration = 0
        for i, track in enumerate(player.queue, start=1):
            embed.add_field(name=f"{i}. {track.title} {format_duration(track.length)}", value=f"by {track.author}", inline=False)
            total_duration += track.length

        embed.set_footer(text=f"Total duration: {format_duration(total_duration)}")
        await ctx.send(embed=embed)

    
    @commands.command(aliases=["lyric"])
    async def lyrics(self, ctx: discord.ApplicationContext, *, song_title: str = None) -> None:
        """Show the lyrics of the specified song or the currently playing song if no title is provided."""
        if song_title is None:
            player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
            if not player or not player.playing:
                await ctx.send("No song is currently playing. Please provide a song title.")
                return
            song_title = player.current.title

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

    @commands.command(aliases=["sound"])
    async def play_sound(self, ctx: discord.ApplicationContext) -> None:
        """Play a random sound from the specified category."""
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
            
        await self.play_random_sound(player, "inactive")

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