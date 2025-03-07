import nextcord
import nextcord.ext.commands as cmd
import lavalink
import asyncio
import logging
import math
import re
from tokens import *
from decorators import log_calls, developer_only
from lavalink.exceptions import NodeException


# ---------------------------- #
# Lavalink Voice Client
# ---------------------------- #
class LavalinkVoiceClient(nextcord.VoiceClient):
    def __init__(self, client: nextcord.Client, channel: nextcord.abc.Connectable):
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
class TempoView(nextcord.ui.View):
    def __init__(self, interaction: nextcord.Interaction):
        super().__init__(timeout=60)
        self.interaction = interaction
        self.message = None
        self.requester = interaction.user
        self.used = False  # Track if the view has been interacted with

    async def on_timeout(self):
        if not self.used and self.message:
            for item in self.children:
                item.disabled = True
            await self.message.edit(view=self)  # Only disable if it was never used


# ---------------------------- #
# Music Cog
# ---------------------------- #
class Music(cmd.Cog):
    # Initialize music cog and set up Lavalink for audio streaming
    def __init__(self, bot):
        self.bot = bot
        self.tempo_ambient_mode = {sourceflow_guild_id: False, dev_guild_id: False}

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

    # Clean up event hooks when music cog is unloaded
    def cog_unload(self):
        self.bot.lavalink._event_hooks.clear()

    # Tempo can play music on its own (Only works in SourceFlow server)
    @log_calls
    async def ambient_mode(self, guild, player):
        try:
            # Check if guild is SourceFlow
            if guild.id not in tempo_guild_ids or not player:
                print("Ambient Mode: Guild ID not in tempo_guild_ids")
                return
            
            # Check whether bot is Tempo or Beta
            if self.bot.user.id == tempo_user_id:
                ambient_channel_id = ambient_channel_id_tempo
            else:
                ambient_channel_id = ambient_channel_id_beta
            
            self.tempo_ambient_mode[guild.id] = True

            results = await player.node.get_tracks(ambient_playlist)
            tracks = results['tracks']

            if not player.is_connected:
                channel = guild.get_channel(ambient_channel_id)
                await channel.connect(cls=LavalinkVoiceClient)

            for song in tracks:
                track = lavalink.models.AudioTrack(song, 488812651514691586, recommended=True)
                player.add(requester=488812651514691586, track=track)

            if not player.is_playing:
                await player.play()
                await player.set_volume(20)
                player.set_repeat(True)
        except:
            print("Ambient Mode: Unknown Error")
            return


    # Automatically inactivity disconnect
    @log_calls
    async def disconnect_timer(self, guild, player, delay):
        if self.tempo_ambient_mode[guild.id] == True:
            print("ambient mode. disconnect timer cancelled.")
            return
        
        for timer in range(delay):
            await asyncio.sleep(1)

            # Cancel disconnect timer if player is playing and users are listening
            if (not guild.voice_client or not player) or (player.is_playing and (len(guild.voice_client.channel.members) > 1)) or self.tempo_ambient_mode.get(guild.id, False) == True:
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
            await self.disconnect_timer(guild, event.player, 180)

    # Runs when user joins, leaves or changes voice channel
    @cmd.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        player = self.bot.lavalink.player_manager.get(member.guild.id)

        # If called by the bot itself
        if member.id == self.bot.user.id:
            # If bot is forcibly disconnected by guild member
            if not after.channel and member.guild.voice_client:
                player.set_repeat(False)
                player.set_shuffle(False)
                player.queue.clear()
                self.tempo_ambient_mode[member.guild.id] = False
                await player.stop()
                await member.guild.voice_client.disconnect(force=True)
                return
            
            # If bot disconnects
            if not after.channel or not member.guild.voice_client:
                if self.tempo_ambient_mode.get(member.guild.id, False) == True:
                    self.tempo_ambient_mode[member.guild.id] = False
                    return
                # If bot disconnects and is in SourceFlow
                if (member.guild.id in tempo_guild_ids and after.channel == None):
                    await self.ambient_mode(member.guild, player)
                return
            
        # If bot is the only member in voice channel
        if member.guild.voice_client and len(member.guild.voice_client.channel.members) == 1:
            await self.disconnect_timer(member.guild, player, 180)

    @log_calls
    @nextcord.slash_command(description="Play a song or add it to the queue.", guild_ids=tempo_guild_ids)
    async def play(self, interaction: nextcord.Interaction, query: str):
        # Create embed message
        embed = nextcord.Embed(color=nextcord.Color.from_rgb(134, 194, 50))

        # Get or create the player
        try:
            player = self.bot.lavalink.player_manager.create(interaction.guild.id, endpoint=str(interaction.guild.region))
        except NodeException as e:
            if "No available nodes" in str(e):
                print("No nodes are available for audio streaming. Please try again shortly.")
                embed.description = ("No nodes are available for audio streaming. Please try again shortly.")
                return await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                raise e  # Re-raise if it's a different NodeException

        # Refresh guild info (voice channel members in this case)
        await interaction.guild.chunk()
        # If Tempo is in passive mode AND there are no other users in its current voice channel, stop it and reset
        if self.tempo_ambient_mode.get(interaction.guild.id, False) and interaction.guild.voice_client and (not len(interaction.guild.voice_client.channel.members) > 1 or interaction.user.voice.channel == interaction.guild.voice_client.channel):
            # Stop any current music and clear the queue
            player.set_repeat(False)
            player.set_shuffle(False)
            player.queue.clear()
            await player.stop()
            self.tempo_ambient_mode[interaction.guild.id] = False

        # If user is not in a voice channel
        if not interaction.user.voice or not interaction.user.voice.channel:
            embed.description = "You must be in a voice channel to use this command."
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # Connect bot to voice channel if needed
        if not interaction.guild.voice_client or interaction.user.voice.channel != interaction.guild.voice_client.channel:
            permissions = interaction.user.voice.channel.permissions_for(interaction.guild.me)
            if not permissions.connect or not permissions.speak:
                embed.description = "Tempo needs `Connect`, `Speak` and `View Channel` permissions."
                return await interaction.response.send_message(embed=embed, ephemeral=True)

            player.store('channel', interaction.channel_id)
            # If not connected to a voice channel
            if not interaction.guild.voice_client:
                await interaction.user.voice.channel.connect(cls=LavalinkVoiceClient)
            else:
                if len(interaction.guild.voice_client.channel.members) > 1:
                    embed.description = "Tempo cannot move to your channel while other users are listening."
                    return await interaction.response.send_message(embed=embed, ephemeral=True)
                else:    
                    await interaction.guild.voice_client.move_to(interaction.user.voice.channel)

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

    @log_calls
    @nextcord.slash_command(description="Stop playback, clear the queue, and disconnect.", guild_ids=tempo_guild_ids)
    async def stop(self, interaction: nextcord.Interaction):
        # Get player for guild from guild cache
        player = interaction.client.lavalink.player_manager.get(interaction.guild.id)

        # Create embed and set border color
        embed = nextcord.Embed(color=nextcord.Color.from_rgb(134, 194, 50))

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

    @log_calls
    @nextcord.slash_command(description="Pause the current song.", guild_ids=tempo_guild_ids)
    async def pause(self, interaction: nextcord.Interaction):

        # Get player for guild from guild cache
        player = interaction.client.lavalink.player_manager.get(interaction.guild.id)

        # Create embed and set border color
        embed = nextcord.Embed(color=nextcord.Color.from_rgb(134, 194, 50))

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

    @log_calls
    @nextcord.slash_command(description="Resume the paused song.", guild_ids=tempo_guild_ids)
    async def resume(self, interaction: nextcord.Interaction):

        # Get player for guild from guild cache
        player = interaction.client.lavalink.player_manager.get(interaction.guild.id)

        # Create embed and set border color
        embed = nextcord.Embed(color=nextcord.Color.from_rgb(134, 194, 50))

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

    @log_calls
    @nextcord.slash_command(description="Skip the current song.", guild_ids=tempo_guild_ids)
    async def skip(self, interaction: nextcord.Interaction):

        # Get player for guild from guild cache
        player = interaction.client.lavalink.player_manager.get(interaction.guild.id)

        # Create embed and set border color
        embed = nextcord.Embed(color=nextcord.Color.from_rgb(134, 194, 50))

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

    @log_calls
    @nextcord.slash_command(description="Restart the current song.", guild_ids=tempo_guild_ids)
    async def restart(self, interaction: nextcord.Interaction):

        # Get player for guild from guild cache
        player = interaction.client.lavalink.player_manager.get(interaction.guild.id)

        # Create embed and set border color
        embed = nextcord.Embed(color=nextcord.Color.from_rgb(134, 194, 50))

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

    @log_calls
    @nextcord.slash_command(description="Seek to a specific position in the current song.", guild_ids=tempo_guild_ids)
    async def seek(self, interaction: nextcord.Interaction, position: int):

        # Get player for guild from guild cache
        player = self.bot.lavalink.player_manager.get(interaction.guild.id)

        # Create embed and set border color
        embed = nextcord.Embed(color=nextcord.Color.from_rgb(134, 194, 50))

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

    @log_calls
    @nextcord.slash_command(description="Get the title of the current song.", guild_ids=tempo_guild_ids)
    async def song(self, interaction: nextcord.Interaction):

        # Get player for guild from guild cache
        player = self.bot.lavalink.player_manager.get(interaction.guild.id)

        # Create embed and set border color
        embed = nextcord.Embed(color=nextcord.Color.from_rgb(134, 194, 50))

        # If player does not exist or isn't playing
        if not player or not player.is_playing:
            embed.description = "No music is currently playing."
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # Get current song title
        track = player.current
        embed.description = f"Now Playing: [{track['title']}]({track['uri']})"
        embed.description += f"\nDuration: `{math.floor(track.duration/1000)} seconds`"

        # Send embed message
        await interaction.response.send_message(embed=embed)

    @log_calls
    @nextcord.slash_command(description="Get a list of all songs in the queue.", guild_ids=tempo_guild_ids)
    async def queue(self, interaction: nextcord.Interaction):

        # Get player for guild from guild cache
        player = self.bot.lavalink.player_manager.get(interaction.guild.id)

        # Create embed and set border color
        embed = nextcord.Embed(color=nextcord.Color.from_rgb(134, 194, 50))
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

    @log_calls
    @nextcord.slash_command(description="Check current playback volume or adjust volume from 1 to 100.", guild_ids=tempo_guild_ids)
    async def volume(self, interaction: nextcord.Interaction, volume: int = None):

        # Get player for guild from guild cache
        player = self.bot.lavalink.player_manager.get(interaction.guild.id)

        # Create embed and set border color
        embed = nextcord.Embed(color=nextcord.Color.from_rgb(134, 194, 50))

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

    @log_calls
    @nextcord.slash_command(description="Toggle repeat mode for the queue.", guild_ids=tempo_guild_ids)
    async def repeat(self, interaction: nextcord.Interaction):

        # Get player for guild from guild cache
        player = self.bot.lavalink.player_manager.get(interaction.guild.id)

        # Create embed and set border color
        embed = nextcord.Embed(color=nextcord.Color.from_rgb(134, 194, 50))

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

    @log_calls
    @nextcord.slash_command(description="Toggle shuffle mode for the queue.", guild_ids=tempo_guild_ids)
    async def shuffle(self, interaction: nextcord.Interaction):

        # Get player for guild from guild cache
        player = self.bot.lavalink.player_manager.get(interaction.guild.id)

        # Create embed and set border color
        embed = nextcord.Embed(color=nextcord.Color.from_rgb(134, 194, 50))

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

    @log_calls
    @nextcord.slash_command(description="Remove a song from the queue by its position.", guild_ids=tempo_guild_ids)
    async def remove(self, interaction: nextcord.Interaction, index: int):

        # Get player for guild from guild cache
        player = self.bot.lavalink.player_manager.get(interaction.guild.id)

        # Create embed and set border color
        embed = nextcord.Embed(color=nextcord.Color.from_rgb(134, 194, 50))

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

    @log_calls
    @nextcord.slash_command(description="Search for a song and choose which one to play.", guild_ids=tempo_guild_ids)
    async def search(self, interaction: nextcord.Interaction, query: str):

        # Ensure player exists before fetching tracks
        player = self.bot.lavalink.player_manager.create(interaction.guild.id, endpoint=str(interaction.guild.region))

        # Remove leading and trailing <>. <> suppress embedding links.
        query = query.strip('<>')

        # Search for given query, get results
        query = f'ytsearch:{query}'
        results = await player.node.get_tracks(query)

        # If no results found
        if not results or not results['tracks']:
            embed = nextcord.Embed(color=nextcord.Color.from_rgb(134, 194, 50))
            embed.description = "No tracks found."
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # Ensure user is in a voice channel
        if not interaction.user.voice or not interaction.user.voice.channel:
            embed = nextcord.Embed(color=nextcord.Color.from_rgb(134, 194, 50))
            embed.description = "You must be in a voice channel to use this command."
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # Custom View that disables itself after selection
        class TempoView(nextcord.ui.View):
            def __init__(self, interaction: nextcord.Interaction):
                super().__init__(timeout=60)  # View expires after 60 seconds
                self.interaction = interaction
                self.message = None
                self.requester = interaction.user
                self.used = False  # Track if the view has been interacted with

            # Disables buttons when timeout occurs, only if no selection was made
            async def on_timeout(self):
                if not self.used and self.message:
                    for item in self.children:
                        item.disabled = True
                    await self.message.edit(view=self)  # Only disable if never used

        # Function to handle track selection
        async def track_select(interaction: nextcord.Interaction):
            track_number = int(interaction.data['custom_id'])
            track = results['tracks'][track_number]
            track = lavalink.models.AudioTrack(track, interaction.user.id, recommended=True)
            player.add(requester=interaction.user.id, track=track)

            # Create embed for response
            embed = nextcord.Embed(color=nextcord.Color.from_rgb(134, 194, 50))
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

            # Mark the view as used to prevent buttons from reappearing
            view.used = True

            # Remove buttons after selection
            await interaction.response.edit_message(embed=embed, view=None)  # Removes the view completely

        # Create view and add buttons for each track
        view = TempoView(interaction)
        for i, track in enumerate(results['tracks'][:5]):  # Limit to 5 results
            track_button = nextcord.ui.Button(
                label=track['info']['title'][:80],  # Limit button label length
                custom_id=str(i),
                row=i % 5,
                style=nextcord.ButtonStyle.secondary  # Matches Dark Gray theme
            )
            track_button.callback = track_select  # Calls track_select when clicked
            view.add_item(track_button)

        # Send view and save as message
        try:
            message = await interaction.response.send_message(embed=nextcord.Embed(
                color=nextcord.Color.from_rgb(134, 194, 50),
                description="Select a song from the list below."
            ), view=view)
            view.message = message  # Store message reference for timeout handling
        except:
            embed = nextcord.Embed(color=nextcord.Color.from_rgb(134, 194, 50))
            embed.description = "Invalid search query."
            return await interaction.response.send_message(embed=embed, ephemeral=True)

    @log_calls
    @developer_only
    @nextcord.slash_command(description="Test command that calls the play command", guild_ids=tempo_guild_ids)
    async def test(self, interaction: nextcord.Interaction):
        test_query = "fade oscuro"
        await self.play(interaction, test_query)


def setup(bot):
    bot.add_cog(Music(bot))