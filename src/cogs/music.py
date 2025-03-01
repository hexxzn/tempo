from nextcord import Interaction, slash_command
from nextcord.ext import commands as cmd
import nextcord as nxt
from tokens import *
import lavalink
import asyncio
import logging
import math
import re


# ---------------------------- #
# Lavalink Voice Client
# ---------------------------- #
class LavalinkVoiceClient(nxt.VoiceClient):
    def __init__(self, client: nxt.Client, channel: nxt.abc.Connectable):
        self.client = client
        self.channel = channel
        self.lavalink = getattr(client, "lavalink", None)

        if not self.lavalink:
            client.lavalink = lavalink.Client(client.user.id)
            client.lavalink.add_node(node_host, node_port, node_password, node_region, node_name)
            self.lavalink = client.lavalink

    async def on_voice_server_update(self, data):
        await self.lavalink.voice_update_handler({"t": "VOICE_SERVER_UPDATE", "d": data})

    async def on_voice_state_update(self, data):
        await self.lavalink.voice_update_handler({"t": "VOICE_STATE_UPDATE", "d": data})

    async def connect(self, *, timeout: float, reconnect: bool) -> None:
        self.lavalink.player_manager.create(self.channel.guild.id)
        await self.channel.guild.change_voice_state(channel=self.channel)

    async def disconnect(self, *, force: bool) -> None:
        player = self.lavalink.player_manager.get(self.channel.guild.id)
        if force or player.is_connected:
            await self.channel.guild.change_voice_state(channel=None)
            player.channel_id = None
            self.cleanup()


# ---------------------------- #
# UI View for Search Command
# ---------------------------- #
class TempoView(nxt.ui.View):
    def __init__(self, interaction: Interaction):
        super().__init__(timeout=60)
        self.interaction = interaction
        self.message = None
        self.requester = interaction.user

    async def on_timeout(self):
        if self.message:
            for item in self.children:
                item.disabled = True
            await self.message.edit(view=self)


# ---------------------------- #
# Music Cog
# ---------------------------- #
class Music(cmd.Cog):
    def __init__(self, bot):
        self.bot = bot

        if not hasattr(bot, "lavalink"):
            bot.lavalink = lavalink.Client(bot.user.id)
            bot.lavalink.add_node(node_host, node_port, node_password, node_region, node_name)

            # Apply Log Filter to Lavalink Logger
            class LavalinkFilter(logging.Filter):
                def filter(self, record):
                    return "Received unknown op: ready" not in record.getMessage()

            lavalink_logger = logging.getLogger("lavalink")  # Correct way to access Lavalink logs
            lavalink_logger.addFilter(LavalinkFilter())  # Suppresses the specific message
            lavalink_logger.setLevel(logging.INFO)  # Reduces excessive debug logs

            lavalink.add_event_hook(self.track_hook)

    def cog_unload(self):
        self.bot.lavalink._event_hooks.clear()

    # Automatically disconnect after inactivity
    async def disconnect_timer(self, guild, player, delay):
        for timer in range(delay):
            await asyncio.sleep(1)
            if not guild.voice_client or player.is_playing:
                return
        player.set_repeat(False)
        player.set_shuffle(False)
        player.queue.clear()
        await player.stop()
        await guild.voice_client.disconnect(force=True)

    # Runs when the music stops
    async def track_hook(self, event):
        if isinstance(event, lavalink.events.QueueEndEvent):
            guild = self.bot.get_guild(int(event.player.guild_id))
            await self.disconnect_timer(guild, event.player, 90)

    # Handle user disconnects
    @cmd.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.id == self.bot.user.id or not member.guild.voice_client:
            return

        player = self.bot.lavalink.player_manager.get(member.guild.id)
        if before.channel == member.guild.voice_client.channel and len(member.guild.voice_client.channel.members) == 1:
            await self.disconnect_timer(member.guild, player, 180)


    @slash_command(description="Play a song or add it to the queue.", guild_ids=[949642805138059285])
    async def play(self, interaction: Interaction, query: str):
        
        # Get or create the player
        player = self.bot.lavalink.player_manager.create(interaction.guild.id, endpoint=str(interaction.guild.region))
        
        # Create embed message
        embed = nxt.Embed(color=nxt.Color.from_rgb(134, 194, 50))

        # If user is not in a voice channel
        if not interaction.user.voice or not interaction.user.voice.channel:
            embed.description = "You must be in a voice channel to use this command."
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # Connect bot to voice channel if needed
        if not player.is_connected:
            permissions = interaction.user.voice.channel.permissions_for(interaction.guild.me)
            if not permissions.connect or not permissions.speak:
                embed.description = "Tempo needs `Connect` and `Speak` permissions."
                return await interaction.response.send_message(embed=embed, ephemeral=True)

            player.store('channel', interaction.channel_id)
            await interaction.user.voice.channel.connect(cls=LavalinkVoiceClient)

        # Search for the query
        query = query.strip('<>')
        url_rx = re.compile(r'https?://(?:www\.)?.+')
        
        if not url_rx.match(query):
            query = f'ytsearch:{query}'

        results = await player.node.get_tracks(query)

        # Handle invalid search results
        if not results or not results['tracks']:
            embed.description = "No tracks found."
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # If query returns a playlist
        if results['loadType'] == 'PLAYLIST_LOADED':
            tracks = results['tracks']

            for song in tracks:
                track = lavalink.models.AudioTrack(song, interaction.user.id, recommended=True)
                player.add(requester=interaction.user.id, track=track)

            embed.description = f'Playlist queued: [{results["playlistInfo"]["name"]}]({query}) ({len(tracks)} tracks)'
        else:
            # Pick the first track (or non-music video)
            track = results['tracks'][0]
            track = lavalink.models.AudioTrack(track, interaction.user.id, recommended=True)
            player.add(requester=interaction.user.id, track=track)

            embed.description = f'Now Playing: [{track.title}]({track.uri})' if not player.is_playing else f'Queued: [{track.title}]({track.uri})'

        # Play the track
        if not player.is_playing:
            await player.play()
            await player.set_volume(20)

        # Send response
        await interaction.response.send_message(embed=embed)


    @slash_command(description="Stop playback, clear the queue, and disconnect the bot.", guild_ids=[949642805138059285])
    async def stop(self, interaction: Interaction):

        # Get player for guild from guild cache
        player = interaction.client.lavalink.player_manager.get(interaction.guild.id)

        # Create embed and set border color
        embed = nxt.Embed(color=nxt.Color.from_rgb(134, 194, 50))

        # If player does not exist or isn't playing
        if not player or not player.is_playing:
            embed.description = "Nothing is currently playing."
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # If user is not in the same voice channel
        if not interaction.user.voice or (player.is_connected and interaction.user.voice.channel.id != int(player.channel_id)):
            embed.description = "You must be in the same voice channel as Tempo to use this command."
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # Stop message
        embed.description = "Tempo has disconnected. \n"

        # If queue has songs, alert user it was cleared
        if len(player.queue) > 0:
            embed.description += "The queue has been cleared. \n"

        # Disable repeat and shuffle
        player.set_repeat(False)
        player.set_shuffle(False)

        # Stop current track
        await player.stop()

        # Clear queue
        player.queue.clear()

        # Disconnect from voice channel
        await interaction.guild.voice_client.disconnect(force=True)

        # Send response
        await interaction.response.send_message(embed=embed)


    @slash_command(description="Pause the current song.", guild_ids=[949642805138059285])
    async def pause(self, interaction: Interaction):

        # Get player for guild from guild cache
        player = interaction.client.lavalink.player_manager.get(interaction.guild.id)

        # Create embed and set border color
        embed = nxt.Embed(color=nxt.Color.from_rgb(134, 194, 50))

        # If player does not exist or isn't playing
        if not player or not player.is_playing:
            embed.description = "Nothing is currently playing."
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # If player is already paused
        if player.paused:
            embed.description = "The music is already paused."
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # Pause playback
        await player.set_pause(True)

        # Send response
        embed.description = "Playback has been paused. Use `/resume` to continue playing."
        await interaction.response.send_message(embed=embed)


    @slash_command(description="Resume the paused song.", guild_ids=[949642805138059285])
    async def resume(self, interaction: Interaction):

        # Get player for guild from guild cache
        player = interaction.client.lavalink.player_manager.get(interaction.guild.id)

        # Create embed and set border color
        embed = nxt.Embed(color=nxt.Color.from_rgb(134, 194, 50))

        # If player does not exist or isn't playing
        if not player or not player.is_playing:
            embed.description = "Nothing is currently playing."
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # If player is not paused
        if not player.paused:
            embed.description = "The music is already playing."
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # Resume playback
        await player.set_pause(False)

        # Send response
        embed.description = "Playback has resumed."
        await interaction.response.send_message(embed=embed)


    @slash_command(description="Skip the current song.", guild_ids=[949642805138059285])
    async def skip(self, interaction: Interaction):

        # Get player for guild from guild cache
        player = interaction.client.lavalink.player_manager.get(interaction.guild.id)

        # Create embed and set border color
        embed = nxt.Embed(color=nxt.Color.from_rgb(134, 194, 50))

        # If player does not exist or isn't playing
        if not player or not player.is_playing:
            embed.description = "Nothing is currently playing."
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # If player is paused
        if player.paused:
            embed.description = "Unable to skip while the player is paused. Use `/resume` to continue playing."
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # Initial embed message content
        if len(player.queue) > 0:
            track = player.queue[0]
            embed.description = f"Now Playing: [{track['title']}]({track['uri']})"
        else:
            track = player.current
            embed.description = f"Skipped: [{track['title']}]({track['uri']})"

        # Notify about repeat and shuffle
        if player.repeat:
            embed.description += "\n Repeat is enabled. Use `/repeat` to disable."
        if player.shuffle:
            embed.description += "\n Shuffle is enabled. Use `/shuffle` to disable."

        # Send embed message before skipping
        await interaction.response.send_message(embed=embed)

        # Skip the current track
        await player.skip()


    @slash_command(description="Restart the current song from the beginning.", guild_ids=[949642805138059285])
    async def restart(self, interaction: Interaction):

        # Get player for guild from guild cache
        player = interaction.client.lavalink.player_manager.get(interaction.guild.id)

        # Create embed and set border color
        embed = nxt.Embed(color=nxt.Color.from_rgb(134, 194, 50))

        # If player does not exist or isn't playing
        if not player or not player.is_playing:
            embed.description = "Nothing is currently playing."
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # If player is paused
        if player.paused:
            embed.description = "Unable to restart while the player is paused. Use `/resume` to continue playing."
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # Restart the track from the beginning
        await player.seek(0)

        # Send embed message
        track = player.current
        embed.description = f"Restarted: [{track['title']}]({track['uri']})"
        await interaction.response.send_message(embed=embed)


    @slash_command(description="Seek to a specific position in the current song.", guild_ids=[949642805138059285])
    async def seek(self, interaction: Interaction, position: int):

        # Get player for guild from guild cache
        player = self.bot.lavalink.player_manager.get(interaction.guild.id)

        # Create embed and set border color
        embed = nxt.Embed(color=nxt.Color.from_rgb(134, 194, 50))

        # If player does not exist or isn't playing
        if not player or not player.is_playing:
            embed.description = "Nothing is currently playing."
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # If player is paused
        if player.paused:
            embed.description = "Unable to seek while the player is paused. Use `/resume` to continue playing."
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # Track duration in seconds
        duration = math.floor(player.current.duration / 1000)

        # Validate user input
        if position < 0 or position > duration:
            embed.description = f"Invalid position. Track length: {duration} seconds. Try `/seek {duration // 2}` to jump halfway."
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # Seek to the specified position
        await player.seek(position * 1000)

        # Send confirmation
        embed.description = f"Seeking to {position} seconds."
        await interaction.response.send_message(embed=embed)


    @slash_command(description="Get the title of the current song.", guild_ids=[949642805138059285])
    async def song(self, interaction: Interaction):

        # Get player for guild from guild cache
        player = self.bot.lavalink.player_manager.get(interaction.guild.id)

        # Create embed and set border color
        embed = nxt.Embed(color=nxt.Color.from_rgb(134, 194, 50))

        # If player does not exist or isn't playing
        if not player or not player.is_playing:
            embed.description = "No music is currently playing."
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # Get current song title
        track = player.current
        embed.description = f"Now Playing: [{track['title']}]({track['uri']})"

        # Send embed message
        await interaction.response.send_message(embed=embed)


    @slash_command(description="View the current song queue.", guild_ids=[949642805138059285])
    async def queue(self, interaction: Interaction):

        # Get player for guild from guild cache
        player = self.bot.lavalink.player_manager.get(interaction.guild.id)

        # Create embed and set border color
        embed = nxt.Embed(color=nxt.Color.from_rgb(134, 194, 50))
        embed.description = ""

        # If player does not exist or isn't playing
        if not player or not player.is_playing:
            embed.description = "No music is currently playing."
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # If queue is empty
        if len(player.queue) == 0:
            embed.description = "The queue is empty."
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # Get all queued song titles
        for index, track in enumerate(player.queue[:10]):  # Limit to first 10 tracks to prevent long messages
            embed.description += f"{index + 1}. [{track['title']}]({track['uri']})\n"

        # Send embed message
        await interaction.response.send_message(embed=embed)


    @slash_command(description="Check or adjust the music volume.", guild_ids=[949642805138059285])
    async def volume(self, interaction: Interaction, volume: int = None):

        # Get player for guild from guild cache
        player = self.bot.lavalink.player_manager.get(interaction.guild.id)

        # Create embed and set border color
        embed = nxt.Embed(color=nxt.Color.from_rgb(134, 194, 50))

        # Get server owner ID
        owner = interaction.guild.owner_id

        # If player does not exist
        if not player:
            embed.description = "No music is currently playing."
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # If no volume is specified, return current volume
        if volume is None:
            embed.description = f"Current volume: {player.volume}%"
            return await interaction.response.send_message(embed=embed)

        # Validate volume range
        if volume < 1 or volume > 100:
            embed.description = "Enter a value from 1 to 100. Example: `/volume 25`."
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # Check if user has permission (server owner only)
        if interaction.user.id != owner:
            embed.description = "Only the server owner can adjust the volume."
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # Get current and new volume
        current_volume = player.volume
        await player.set_volume(volume)

        # Respond based on change
        if volume > current_volume:
            embed.description = f"Volume increased from {current_volume}% to {volume}%."
        elif volume < current_volume:
            embed.description = f"Volume decreased from {current_volume}% to {volume}%."
        else:
            embed.description = f"Volume is already set to {volume}%."

        # Send embed message
        await interaction.response.send_message(embed=embed)


    @slash_command(description="Toggle repeat mode for the current song.", guild_ids=[949642805138059285])
    async def repeat(self, interaction: Interaction):

        # Get player for guild from guild cache
        player = self.bot.lavalink.player_manager.get(interaction.guild.id)

        # Create embed and set border color
        embed = nxt.Embed(color=nxt.Color.from_rgb(134, 194, 50))

        # If player does not exist or isn't playing
        if not player or not player.is_playing:
            embed.description = "No music is currently playing."
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # Toggle repeat
        player.set_repeat(not player.repeat)
        status = "enabled" if player.repeat else "disabled"

        # Send response
        embed.description = f"Repeat mode has been **{status}**."
        await interaction.response.send_message(embed=embed)


    @slash_command(description="Toggle shuffle mode for the queue.", guild_ids=[949642805138059285])
    async def shuffle(self, interaction: Interaction):

        # Get player for guild from guild cache
        player = self.bot.lavalink.player_manager.get(interaction.guild.id)

        # Create embed and set border color
        embed = nxt.Embed(color=nxt.Color.from_rgb(134, 194, 50))

        # If player does not exist or queue is empty
        if not player or not player.queue:
            embed.description = "The queue is empty, nothing to shuffle."
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # Toggle shuffle
        player.set_shuffle(not player.shuffle)
        status = "enabled" if player.shuffle else "disabled"

        # Send response
        embed.description = f"Shuffle mode has been **{status}**."
        await interaction.response.send_message(embed=embed)


    @slash_command(description="Remove a song from the queue by its position.", guild_ids=[949642805138059285])
    async def remove(self, interaction: Interaction, index: int):

        # Get player for guild from guild cache
        player = self.bot.lavalink.player_manager.get(interaction.guild.id)

        # Create embed and set border color
        embed = nxt.Embed(color=nxt.Color.from_rgb(134, 194, 50))

        # If player does not exist or queue is empty
        if not player or not player.queue:
            embed.description = "The queue is empty, nothing to remove."
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # Validate user input
        if index < 1 or index > len(player.queue):
            embed.description = f"Invalid position. The queue has {len(player.queue)} tracks. Try `/remove {len(player.queue)}` to remove the last song."
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # Get track from queue
        track = player.queue.pop(index - 1)

        # Embed message content
        embed.description = f"Removed: [{track['title']}]({track['uri']})"

        # Send embed message
        await interaction.response.send_message(embed=embed)


    @slash_command(description="Search for a song and choose which one to play.", guild_ids=[949642805138059285])
    async def search(self, interaction: Interaction, query: str):

        # Ensure player exists before fetching tracks
        player = self.bot.lavalink.player_manager.create(interaction.guild.id, endpoint=str(interaction.guild.region))

        # Remove leading and trailing <>. <> suppress embedding links.
        query = query.strip('<>')

        # Search for given query, get results
        query = f'ytsearch:{query}'
        results = await player.node.get_tracks(query)

        # If no results found
        if not results or not results['tracks']:
            embed = nxt.Embed(color=nxt.Color.from_rgb(134, 194, 50))
            embed.description = "No tracks found."
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # Ensure user is in a voice channel
        if not interaction.user.voice or not interaction.user.voice.channel:
            embed = nxt.Embed(color=nxt.Color.from_rgb(134, 194, 50))
            embed.description = "You must be in a voice channel to use this command."
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # Create a view for buttons
        view = TempoView(interaction)
        view.requester = interaction.user  # Ensure only the requester can interact

        # Function to handle track selection
        async def track_select(interaction: Interaction):
            track_number = int(interaction.data['custom_id'])
            track = results['tracks'][track_number]
            track = lavalink.models.AudioTrack(track, interaction.user.id, recommended=True)
            player.add(requester=interaction.user.id, track=track)

            # Create embed for response
            embed = nxt.Embed(color=nxt.Color.from_rgb(134, 194, 50))
            embed.description = f"Now Playing: [{track.title}]({track.uri})" if not player.is_playing else f"Queued: [{track.title}]({track.uri})"

            # Ensure bot joins the voice channel if not already connected
            if not player.is_connected:
                permissions = interaction.user.voice.channel.permissions_for(interaction.guild.me)
                if not permissions.connect or not permissions.speak:
                    embed.description = "Tempo needs `Connect` and `Speak` permissions."
                    return await interaction.response.send_message(embed=embed, ephemeral=True)

                player.store('channel', interaction.channel_id)
                await interaction.user.voice.channel.connect(cls=LavalinkVoiceClient)

            # Play track and set volume
            if not player.is_playing:
                await player.play()
                await player.set_volume(20)

            # Remove buttons after selection
            await interaction.response.edit_message(embed=embed, view=None)  # Removes the view completely

        # Add buttons for each track
        for i, track in enumerate(results['tracks'][:5]):  # Limit to 5 results
            track_button = nxt.ui.Button(
                label=track['info']['title'][:80],  # Limit button label length
                custom_id=str(i),
                row=i % 5,
                style=nxt.ButtonStyle.secondary  # Matches Dark Gray theme
            )
            track_button.callback = track_select  # Calls track_select when clicked
            view.add_item(track_button)

        # Send view and save as message
        try:
            message = await interaction.response.send_message(view=view)
            view.message = message
        except:
            embed = nxt.Embed(color=nxt.Color.from_rgb(134, 194, 50))
            embed.description = "Invalid search query."
            return await interaction.response.send_message(embed=embed, ephemeral=True)



# Add cog
def setup(bot):
    bot.add_cog(Music(bot))