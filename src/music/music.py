import logging
import random
from typing import cast
import discord
from discord.ext import commands
import lyricsgenius
import wavelink
from client import Bot
from utils.format import format_duration


class CustomContext(commands.Context):
    async def send_embed(self, delete_after=None, **kwargs) -> None:
        embed = discord.Embed(**kwargs)
        await self.send(embed=embed, delete_after=delete_after)


class Music(commands.Cog):
    def __init__(self, bot: Bot, GENIUS_TOKEN: str) -> None:
        self.bot: Bot = bot
        self.genius = lyricsgenius.Genius(GENIUS_TOKEN)
        wavelink.Player.inactive_timeout = 5
        bot.get_context = self.get_context
    
    async def get_context(self, message, *, cls=CustomContext):
        return await super(Bot, self.bot).get_context(message, cls=cls)

    async def play_random_sound(self, player: wavelink.Player, category: str) -> None:
        try:
            category_map = {
                "inactive": {
                    "sleepy": "https://soundcloud.com/vermil-1554451/sleepy",
                    "music_taste": "https://soundcloud.com/vermil-1554451/elevenlabs_2025-01",
                    "soquiet": "https://soundcloud.com/vermil-1554451/soqueit",
                    "songrunningout": "https://soundcloud.com/vermil-1554451/songrun",
                    "sawadeeka": "https://soundcloud.com/vermil-1554451/sawadeeka",
                },
                "hello": {
                    "hello": "https://soundcloud.com/vermil-1554451/playwelcome",
                },
            }

            sounds = category_map.get(category, None)
            if sounds is None:
                logging.error(
                    f"Category {category} does not exist in the category map."
                )
                return

            sound_link = random.choice(list(sounds.values()))
            tracks = await wavelink.Playable.search(sound_link)

            if not tracks:
                logging.error("No tracks found for the given YouTube link.")
                return

            track = tracks[0]
            await player.play(track, add_history=False, volume=70)

        except Exception as e:
            logging.error(f"Failed to play sound: {e}")

    @commands.Cog.listener()
    async def on_wavelink_node_ready(
        self, payload: wavelink.NodeReadyEventPayload
    ) -> None:
        logging.info(
            "Wavelink Node connected: %r | Resumed: %s", payload.node, payload.resumed
        )

    # Handle inactive player with random sound
    @commands.Cog.listener()
    async def on_wavelink_inactive_player(self, player: wavelink.Player) -> None:
        await self.play_random_sound(player, "inactive")

    @commands.command(aliases=["p"])
    async def play(self, ctx: CustomContext, *, query: str) -> None:
        """Play a song with the given query."""
        if not ctx.guild:
            return

        player: wavelink.Player
        player = cast(wavelink.Player, ctx.voice_client)  # type: ignore

        if not player:
            try:
                player = await ctx.author.voice.channel.connect(cls=wavelink.Player)  # type: ignore
                await self.play_random_sound(player, "hello")

            except AttributeError:
                await ctx.send_embed(
                    description="Please join a voice channel first before using this command.",
                    color=discord.Color.red(),
                )
                return
            except discord.ClientException:
                await ctx.send_embed(
                    description="I was unable to join this voice channel. Please try again.",
                    color=discord.Color.red(),
                )
                return

        player.autoplay = wavelink.AutoPlayMode.partial

        if not hasattr(player, "home"):
            player.home = ctx.channel
        elif player.home != ctx.channel:
            await ctx.send_embed(
                description=f"You can only play songs in {player.home.mention}, as the player has already started there.",
                color=discord.Color.red(),
            )
            return

        if "youtube.com" in query or "youtu.be" in query:
            tracks: wavelink.Search = await wavelink.Playable.search(query)
        elif "soundcloud.com" in query:
            tracks: wavelink.Search = await wavelink.Playable.search(query)
        elif "spotify.com" in query:
            tracks: wavelink.Search = await wavelink.Playable.search(query)
        else:
            tracks: wavelink.Search = await wavelink.Playable.search(
                query, source=wavelink.TrackSource.YouTubeMusic
            )

        if not tracks:
            await ctx.send_embed(
                description=f"{ctx.author.mention} - Could not find any tracks with that query. Please try again.",
                color=discord.Color.red(),
            )
            return

        # Handle max queue duration
        total_length = sum(track.length for track in player.queue._items)
        if total_length + tracks[0].length > 7200000:  # 2 hours in milliseconds
            await ctx.send_embed(
                description=f"{ctx.author.mention} - Adding this track would exceed the maximum queue duration of 2 hours.",
                color=discord.Color.red(),
            )
            return

        if isinstance(tracks, wavelink.Playlist):
            added: int = await player.queue.put_wait(tracks)
            tracks_length = sum(_track.length for _track in tracks)
            await ctx.send_embed(
                description=(
                    f"Added the playlist **`[{tracks.name}]({tracks.url})`** ({added} songs) to the queue.\n"
                    f"Playlist Duration: **`{format_duration(tracks_length)}`**\n"
                    f"Songs in the queue: **`{len(player.queue)}`**\n"
                    f"Total Duration: **`{format_duration(total_length + tracks_length)}`**"
                ),
                color=discord.Color.green(),
            )
        else:
            track: wavelink.Playable = tracks[0]
            await player.queue.put_wait(track)
            await ctx.send_embed(
                description=(
                    f"Added **[{track.title}]({track.uri})** to the queue.\n"
                    f"Duration: **`{format_duration(track.length)}`**\n"
                    f"Songs in the queue: **`{len(player.queue)}`**\n"
                    f"Total Duration: **`{format_duration(total_length + track.length)}`**"
                ),
                color=discord.Color.green(),
            )

        if not hasattr(player, "history"):
            player.history = []
        player.history.append(track)
        if len(player.history) > 10:
            player.history.pop(0)

        if not player.playing:
            await player.play(player.queue.get(), volume=30)

        try:
            await ctx.message.delete()
        except discord.HTTPException:
            pass

    @commands.command(aliases=["np", "nowplaying"])
    async def now_playing(self, ctx: CustomContext) -> None:
        """Display the currently playing song."""
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        if not player or not player.playing:
            await ctx.send_embed(
                description="No song is currently playing.", color=discord.Color.red()
            )
            return

        track = player.current
        embed = discord.Embed(title="Now Playing", color=discord.Color.green())
        embed.description = (
            f"**[{track.title}]({track.uri})** by `{track.author}`\n"
            f"Song Duration: **`{format_duration(track.length)}`**\n"
            f"Songs in the queue: **`{len(player.queue)}`**\n"
            f"Total Duration: **`{format_duration(sum(_track.length for _track in player.queue._items) + track.length)}`**"
        )

        if track.album.name:
            embed.add_field(name="Album", value=track.album.name)

        await ctx.send(embed=embed)

    @commands.command(aliases=["s"])
    async def skip(self, ctx: CustomContext) -> None:
        """Skip the current song."""
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        if not player:
            return

        await player.skip(force=True)
        await ctx.send_embed(
            description="Skipped the current song.", color=discord.Color.red()
        )
        await ctx.message.add_reaction("❤️")

    @commands.command(aliases=["f"])
    async def filter(self, ctx: CustomContext, mode: str) -> None:
        """Set the filter to a specified style."""
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        if not player:
            return

        filters: wavelink.Filters = player.filters
        if mode.lower() == "karaoke":
            filters.karaoke.set(
                level=1.0, mono_level=1.0, filter_band=220.0, filter_width=100.0
            )
        elif mode.lower() == "nightcore":
            filters.timescale.set(pitch=1.2, speed=1.2, rate=1)
        elif mode.lower() == "sigma":
            filters.timescale.set(pitch=0.8, speed=0.8, rate=1)
        elif mode.lower() == "reset":
            filters.timescale.reset()
            filters.karaoke.reset()
        else:
            await ctx.send_embed(
                description="Invalid mode. Please choose from 'karaoke', 'nightcore', 'sigma', or 'reset'.",
                color=discord.Color.red(),
            )
            return

        await player.set_filters(filters)
        await ctx.send_embed(
            description=f"Set filter to {mode}.", color=discord.Color.red()
        )
        await ctx.message.add_reaction("❤️")

    @commands.command(name="toggle", aliases=["pause", "resume", "t"])
    async def pause_resume(self, ctx: CustomContext) -> None:
        """Pause or Resume the Player depending on its current state."""
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        if not player:
            return

        await player.pause(not player.paused)
        state = "Paused" if player.paused else "Resumed"
        await ctx.send_embed(
            description=f"{state} the player.", color=discord.Color.red()
        )
        await ctx.message.add_reaction("❤️")

    @commands.command(aliases=["v"])
    async def volume(self, ctx: CustomContext, value: int) -> None:
        """Change the volume of the player."""
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        if not player:
            return

        if value < 0 or value > 100:
            await ctx.send_embed(
                description="Volume must be between 0 and 100.",
                color=discord.Color.red(),
            )
            return

        await player.set_volume(value)
        await ctx.send_embed(
            description=f"Set volume to {value}.", color=discord.Color.red()
        )
        await ctx.message.add_reaction("❤️")

    @commands.command(aliases=["dc", "leave", "stop"])
    async def disconnect(self, ctx: CustomContext) -> None:
        """Disconnect the Player."""
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        if not player:
            return

        await player.disconnect()
        await ctx.send_embed(
            description="Stopped the player.", color=discord.Color.red()
        )
        await ctx.message.add_reaction("❤️")

    @commands.command(aliases=["q"])
    async def queue(self, ctx: CustomContext) -> None:
        """Display the current queue."""
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        if not player or not player.queue:
            await ctx.send_embed(
                description="The queue is currently empty.", color=discord.Color.red()
            )
            return

        embed = discord.Embed(title="Current Queue")

        if player.playing:
            current_track = player.current
            embed.add_field(
                name="Now Playing",
                value=f"**[{current_track.title}]({current_track.uri})** by `{current_track.author}` [{format_duration(current_track.length)}]",
                inline=False,
            )

        total_duration = 0
        for i, track in enumerate(player.queue, start=1):
            embed.add_field(
                name=f"{i}. [{track.title}]({track.uri}) {format_duration(track.length)}",
                value=f"by {track.author}",
                inline=False,
            )
            total_duration += track.length

        embed.set_footer(text=f"Total duration: {format_duration(total_duration)}")
        await ctx.send(embed=embed)

    @commands.command(aliases=["history"])
    async def song_history(self, ctx: CustomContext) -> None:
        """Display the history of played songs."""
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        if not player or not hasattr(player, "history") or not player.history:
            await ctx.send_embed(
                description="No song history available.", color=discord.Color.red()
            )
            return

        embed = discord.Embed(
            title="Song History (Last 10 Songs)", color=discord.Color.yellow()
        )
        for i, track in enumerate(player.history, start=1):
            embed.add_field(
                name=f"{i}. [{track.title}]({track.uri}) {format_duration(track.length)}",
                value=f"by {track.author}",
                inline=False,
            )

        await ctx.send(embed=embed)

    @commands.command(aliases=["lyric"])
    async def lyrics(self, ctx: CustomContext, *, song_title: str = None) -> None:
        """Show the lyrics of the specified song or the currently playing song if no title is provided."""
        if song_title is None:
            player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
            if not player or not player.playing:
                await ctx.send_embed(
                    description="No song is currently playing. Please provide a song title.",
                    color=discord.Color.red(),
                )
                return
            song_title = player.current.title

        try:
            await ctx.send_embed(
                description=f"Searching for lyrics of `{song_title}`...",
                color=discord.Color.blue(),
                delete_after=10,
            )
            song = self.genius.search_song(song_title)
            if song:
                embed = discord.Embed(
                    title=f"Lyrics for `{song.title}` by `{song.artist}`",
                    description=song.lyrics[:4096],
                    url=song.url,
                    color=discord.Color.yellow(),
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send_embed(
                    description=f"Could not find lyrics for `{song_title}`.",
                    color=discord.Color.red(),
                    delete_after=10,
                )
        except Exception as e:
            await ctx.send_embed(
                description=f"An error occurred while fetching lyrics: {e}",
                color=discord.Color.red(),
            )

    @commands.command()
    async def seek(self, ctx: CustomContext, position: str) -> None:
        """Seek to a specific position in the currently playing song."""
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        if not player or not player.playing:
            await ctx.send_embed(
                description="No song is currently playing.", color=discord.Color.red()
            )
            return

        try:
            time_parts = list(map(int, position.split(":")))
            if len(time_parts) == 1:
                seconds = time_parts[0]
            elif len(time_parts) == 2:
                seconds = time_parts[0] * 60 + time_parts[1]
            elif len(time_parts) == 3:
                seconds = time_parts[0] * 3600 + time_parts[1] * 60 + time_parts[2]
            else:
                await ctx.send_embed(
                    description="Invalid time format. Use MM:SS or HH:MM:SS.",
                    color=discord.Color.red(),
                )
                return

            await player.seek(seconds * 1000)
            await ctx.send_embed(
                description=f"Seeked to {position}.", color=discord.Color.red()
            )
        except ValueError:
            await ctx.send_embed(
                description="Invalid time format. Use MM:SS or HH:MM:SS.",
                color=discord.Color.red(),
            )

    @commands.command(aliases=["sound"])
    async def play_sound(self, ctx: CustomContext) -> None:
        """Play a random sound from the specified category."""
        if not ctx.guild:
            return

        player: wavelink.Player
        player = cast(wavelink.Player, ctx.voice_client)  # type: ignore

        if not player:
            try:
                player = await ctx.author.voice.channel.connect(cls=wavelink.Player)  # type: ignore

            except AttributeError:
                await ctx.send_embed(
                    description="Please join a voice channel first before using this command.",
                    color=discord.Color.red(),
                )
                return
            except discord.ClientException:
                await ctx.send_embed(
                    description="I was unable to join this voice channel. Please try again.",
                    color=discord.Color.red(),
                )
                return

        await self.play_random_sound(player, "inactive")
