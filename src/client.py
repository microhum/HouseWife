import logging
import os
import discord
from discord.ext import commands
import wavelink
import lyricsgenius

class Bot(commands.Bot):
    def __init__(self, GENIUS_TOKEN="YOUR_GENIUS_API_TOKEN") -> None:
        self.GENIUS_TOKEN = GENIUS_TOKEN
        self.genius = lyricsgenius.Genius(self.GENIUS_TOKEN)

        # Intents setup
        intents: discord.Intents = discord.Intents.default()
        intents.message_content = True
        
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

    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload) -> None:
        logging.info("Wavelink Node connected: %r | Resumed: %s", payload.node, payload.resumed)

    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload) -> None:
        player: wavelink.Player | None = payload.player
        if not player:
            # Handle edge cases...
            return

        original: wavelink.Playable | None = payload.original
        track: wavelink.Playable = payload.track

        embed: discord.Embed = discord.Embed(title="Now Playing")
        embed.description = f"**{track.title}** by `{track.author}`"

        if track.artwork:
            embed.set_image(url=track.artwork)

        if original and original.recommended:
            embed.description += f"\n\n`This track was recommended via {track.source}`"

        if track.album.name:
            embed.add_field(name="Album", value=track.album.name)

        embed_lyrics: discord.Embed = discord.Embed()
        try:
            song = self.genius.search_song(track.title)
            if song:
                embed_lyrics.title = f"Lyrics for {song.title} by {song.artist}"
                embed_lyrics.description = song.lyrics[:4096]
            else:
                embed_lyrics.title = f"Could not find lyrics for {track.title}."
        except Exception as e:
            embed_lyrics.title = f"An error occurred while fetching lyrics: {e}"

        await player.home.send(embed=embed)
        await player.home.send(embed=embed_lyrics)