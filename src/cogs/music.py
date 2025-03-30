import nextcord
import nextcord.ext.commands as cmd
import lavalink
import asyncio
import logging
import math
import re
from decorators import log_calls, developer_only, catch_command_errors
from utils import tempo_embed
from tokens import *

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

            self.bot.lavalink.add_event_hook(self.track_hook)

    # Clean up event hooks when music cog is unloaded
    def cog_unload(self):
        self.bot.lavalink._event_hooks.clear()

    # # Tempo can play music on its own (Only works in SourceFlow server)
    # @log_calls
    # async def ambient_mode(self, guild, player):
    #     try:
    #         # Check if guild is SourceFlow
    #         if guild.id not in tempo_guild_ids or not player:
    #             print("Ambient Mode: Guild ID not in tempo_guild_ids")
    #             return
            
    #         # Check whether bot is Tempo or Beta
    #         if self.bot.user.id == tempo_user_id:
    #             ambient_channel_id = ambient_channel_id_tempo
    #         else:
    #             ambient_channel_id = ambient_channel_id_beta
            
    #         self.tempo_ambient_mode[guild.id] = True

    #         try:
    #             results = await player.node.get_tracks(ambient_playlist)
    #         except:
    #             return
            
    #         tracks = results['tracks']

    #         if not player.is_connected:
    #             channel = guild.get_channel(ambient_channel_id)
    #             await channel.connect(cls=LavalinkVoiceClient)

    #         for song in tracks:
                  #
                  #
                  # NEEDS _create_track
                  #
                  #
    #             track = lavalink.AudioTrack(song, 488812651514691586, recommended=True)
    #             player.add(requester=488812651514691586, track=track)

    #         if not player.is_playing:
    #             await player.play()
    #             await player.set_volume(20)
    #             player.loop = 2
    #     except:
    #         print("Ambient Mode: Unknown Error")
    #         return

    # Get lavalink player for guild
    async def _get_player(self, interaction):
        guild_id = interaction.guild.id if interaction.guild else None
        guild_name = interaction.guild.name if interaction.guild else None
        if not guild_id:
            logging.warning("[Player Access] No guild ID found in interaction.")
            embed = tempo_embed("This command must be used in a server.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return None

        player = self.bot.lavalink.player_manager.get(guild_id)
        if not player:
            logging.warning(f"[Player Access] No player found for guild ID: {guild_id}.")
            embed = tempo_embed(f"No player found for guild: {guild_name}")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return None

        return player

    # Get track for current player
    def _get_current_track(self, player):
        track = player.current
        if not track:
            logging.warning("[Track Access] Tried to access current track, but it's None.")
            return None
        return track
    
    # Create track object safely
    def _create_track(self, raw_track_data, requester_id):
        try:
            return lavalink.AudioTrack(raw_track_data, requester_id, recommended=True)
        except Exception as e:
            logging.warning(f"[Track Error] Failed to create AudioTrack: {e}")
            return None

    # Check both user and bot voice state
    async def _check_voice_state(self, interaction, player):
        # If Tempo is not connected to a voice channel
        if not player.is_connected:
            embed = tempo_embed("Tempo is not connected to a voice channel.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        
        # Refresh guild info for accurate member voice channel data (Might be unnecessary? Idk. Keeping it for now.)
        await interaction.guild.chunk()

        # If user is not in the same voice channel as Tempo
        if not interaction.user.voice or interaction.user.voice.channel.id != int(player.channel_id):
            embed = tempo_embed("You must be in the same voice channel as Tempo to use this command.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        
        return True

    # Automatic inactivity disconnect
    @log_calls
    async def disconnect_timer(self, guild, player, delay):
        # if self.tempo_ambient_mode[guild.id] == True:
        #     print("ambient mode. disconnect timer cancelled.")
        #     return
        
        for timer in range(delay):
            await asyncio.sleep(1)

            # Cancel disconnect timer if player is playing and users are listening
            if (not guild.voice_client or not player) or (player.is_playing and (len(guild.voice_client.channel.members) > 1)) or self.tempo_ambient_mode.get(guild.id, False) == True:
                return

        player.loop = 0
        player.shuffle = False
        player.queue.clear()
        await player.stop()
        await guild.voice_client.disconnect(force=True)

    # Runs when the music stops
    async def track_hook(self, event):
        # If Tempo runs out of songs to play
        if isinstance(event, lavalink.events.QueueEndEvent):
            guild = self.bot.get_guild(int(event.player.guild_id))
            await self.disconnect_timer(guild, event.player, 180)

        # If Tempo can't play a song
        elif isinstance(event, lavalink.events.TrackExceptionEvent):
            await event.player.skip()
            logging.error(f"[TrackException] Error on track: {event.track.identifier}\n{event.exception}")

    # Runs when user joins, leaves or changes voice channel
    @cmd.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        player = self.bot.lavalink.player_manager.get(member.guild.id)

        # If called by the bot itself
        if member.id == self.bot.user.id:
            # If bot is forcibly disconnected by guild member
            if not after.channel and member.guild.voice_client:
                player.loop = 0
                player.shuffle = False
                player.queue.clear()
                # self.tempo_ambient_mode[member.guild.id] = False
                await player.stop()
                await member.guild.voice_client.disconnect(force=True)
                return
            
            # If bot disconnects
            if not after.channel or not member.guild.voice_client:
                if self.tempo_ambient_mode.get(member.guild.id, False) == True:
                    # self.tempo_ambient_mode[member.guild.id] = False
                    return
                # If bot disconnects and is in SourceFlow
                if (member.guild.id in tempo_guild_ids and after.channel == None):
                    # await self.ambient_mode(member.guild, player)
                    pass
                return
            
        # If bot is the only member in voice channel
        if member.guild.voice_client and len(member.guild.voice_client.channel.members) == 1:
            await self.disconnect_timer(member.guild, player, 180)

    # Needs cleaning
    @log_calls
    @catch_command_errors
    @nextcord.slash_command(description="Play a song or add it to the queue.", guild_ids=tempo_guild_ids)
    async def play(self, interaction: nextcord.Interaction, query: str = nextcord.SlashOption(description="Song name or URL to play")):
        embed = tempo_embed()
        
        # Attempt to get or create the player.
        try:
            player = self.bot.lavalink.player_manager.create(interaction.guild.id, endpoint=str(interaction.guild.region))
        except:
            embed.description = "Error: Lost connection to audio streaming node. Please try again later."
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # Refresh guild info to update voice channel member data.
        await interaction.guild.chunk()

        # Reset ambient mode if needed.
        # if (self.tempo_ambient_mode.get(interaction.guild.id, False) and
        #     interaction.guild.voice_client and
        #     (len(interaction.guild.voice_client.channel.members) <= 1 or 
        #     interaction.user.voice.channel == interaction.guild.voice_client.channel)):
        #     player.loop = 0
        #     player.shuffle = False
        #     player.queue.clear()
        #     await player.stop()
        #     self.tempo_ambient_mode[interaction.guild.id] = False

        # Check if user is in a voice channel.
        if not (interaction.user.voice and interaction.user.voice.channel):
            embed.description = "You must be in a voice channel to use this command."
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # Check and connect/move bot if necessary.
        user_vc = interaction.user.voice.channel
        bot_vc = interaction.guild.voice_client
        if not bot_vc or user_vc != bot_vc.channel:
            perms = user_vc.permissions_for(interaction.guild.me)
            if not (perms.connect and perms.speak):
                embed.description = "Tempo needs `Connect`, `Speak` and `View Channel` permissions."
                return await interaction.response.send_message(embed=embed, ephemeral=True)
            player.store('channel', interaction.channel_id)
            if not bot_vc:
                await user_vc.connect(cls=LavalinkVoiceClient)
            else:
                # Prevent moving if there are other listeners.
                if len(bot_vc.channel.members) > 1:
                    embed.description = "Tempo cannot move to your channel while other users are listening."
                    return await interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    await bot_vc.move_to(user_vc)

        # Process the query: if not a URL, perform a YouTube search.
        query = query.strip('<>')
        url_pattern = re.compile(r'https?://(?:www\.)?.+')
        if not url_pattern.match(query):
            query = f'ytsearch:{query}'

        try:
            results = await player.node.get_tracks(query)
        except:
            embed.description = "Error: Lost connection to audio streaming node. Please try again later."
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        
        if not results or not results['tracks']:
            embed.description = "No tracks found."
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # Handle playlist or single track.
        if results['loadType'] == 'playlist':
            tracks = results['tracks']
            for song in tracks:
                track_obj = self._create_track(song, interaction.user.id)
                if not track_obj:
                    embed.description = "Error loading track."
                    return await interaction.response.send_message(embed=embed, ephemeral=True)
                player.add(requester=interaction.user.id, track=track_obj)
            embed.description = f'Playlist queued: [{results["playlistInfo"]["name"]}]({query}) ({len(tracks)} tracks)'
        else:
            track_obj = self._create_track(results['tracks'][0], interaction.user.id)
            if not track_obj:
                embed.description = "Error loading track."
                return await interaction.response.send_message(embed=embed, ephemeral=True)
            player.add(requester=interaction.user.id, track=track_obj)
            embed.description = (f'Now Playing: [{track_obj.title}]({track_obj.uri})'
                                if not player.is_playing else
                                f'Queued: [{track_obj.title}]({track_obj.uri})')

        # Start playback if not already playing.
        if not player.is_playing:
            await player.play()
            await player.set_volume(20)

        await interaction.response.send_message(embed=embed)
    
    # Needs cleaning
    @log_calls
    @catch_command_errors
    @nextcord.slash_command(description="Search for a song and choose which one to play.", guild_ids=tempo_guild_ids)
    async def search(self, interaction: nextcord.Interaction, query: str = nextcord.SlashOption(description="Search keywords or URL")):
        embed = tempo_embed()
        
        # Create or get player
        try:
            player = self.bot.lavalink.player_manager.create(interaction.guild.id, endpoint=str(interaction.guild.region))
        except:
            embed.description = "Error: Lost connection to audio streaming node. Please try again later."
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # Process query
        query = query.strip('<>')
        url_pattern = re.compile(r'https?://(?:www\.)?.+')
        if not url_pattern.match(query):
            query = f'ytsearch:{query}'
        
        try:
            results = await player.node.get_tracks(query)
        except:
            embed.description = "Error: Lost connection to audio streaming node. Please try again later."
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        
        if not results or not results['tracks']:
            embed.description = "No tracks found."
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Ensure the user is in a voice channel
        if not (interaction.user.voice and interaction.user.voice.channel):
            embed.description = "You must be in a voice channel to use this command."
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Define a custom dropdown for choosing a track
        class TrackDropdown(nextcord.ui.Select):
            def __init__(self, tracks, interaction, music_cog):
                self.tracks = tracks
                self.interaction = interaction
                self.music_cog = music_cog  # Store reference to Music class

                options = [
                    nextcord.SelectOption(label=track['info']['title'][:80], value=str(i))
                    for i, track in enumerate(tracks[:10])
                ]
                super().__init__(placeholder="Select a track...", min_values=1, max_values=1, options=options)

            async def callback(self, dropdown_interaction: nextcord.Interaction):
                track_index = int(self.values[0])
                selected_track = self.tracks[track_index]

                # ✅ Use Music class to create track safely
                track_obj = self.music_cog._create_track(selected_track, self.interaction.user.id)
                if not track_obj:
                    await dropdown_interaction.response.send_message("Failed to load track.", ephemeral=True)
                    return
                
                # Ensure bot joins voice channel
                user_vc = interaction.user.voice.channel
                bot_vc = interaction.guild.voice_client
                if not bot_vc:
                    await user_vc.connect(cls=LavalinkVoiceClient)
                else:
                    if bot_vc.channel != user_vc:
                        await bot_vc.move_to(user_vc)
                
                # Add track to queue.
                player.add(requester=interaction.user.id, track=track_obj)
                
                # If not currently playing, start playback
                if not player.is_playing:
                    await player.play()
                    await player.set_volume(20)
                
                # Prepare confirmation embed
                confirm_embed = tempo_embed()
                if not player.is_playing:
                    confirm_embed.description = f"Now Playing: [{track_obj.title}]({track_obj.uri})"
                else:
                    confirm_embed.description = f"Queued: [{track_obj.title}]({track_obj.uri})"
                
                # Edit dropdown interaction response
                await dropdown_interaction.response.edit_message(embed=confirm_embed, view=None)
        
        # Create view that contains dropdown
        class DropdownView(nextcord.ui.View):
            def __init__(self, tracks, interaction, music_cog):
                super().__init__(timeout=60)
                self.add_item(TrackDropdown(tracks, interaction, music_cog))
                self.message = None

            async def on_timeout(self):
                # If no selection made after 60 seconds, delete message
                if self.message:
                    try:
                        await self.message.delete()
                    except Exception as e:
                        print(f"Error deleting message on timeout: {e}")
        
        view = DropdownView(results['tracks'], interaction, self)
        embed.description = "Select a track from the dropdown below."
        try:
            msg = await interaction.response.send_message(embed=embed, view=view)
            view.message = msg
        except Exception:
            embed.description = "Invalid search query."
            return await interaction.response.send_message(embed=embed, ephemeral=True)

    # Cleaned
    @log_calls
    @catch_command_errors
    @nextcord.slash_command(description="Stop playback, clear the queue, and disconnect.", guild_ids=tempo_guild_ids)
    async def stop(self, interaction: nextcord.Interaction):
        # Get player for current guild
        player = await self._get_player(interaction)

        # If Tempo is not connected to voice channel or not in same voice channel as user
        if not player or not await self._check_voice_state(interaction, player): 
            return

        # Proceed with stop command
        else:
            embed = tempo_embed("Tempo has disconnected.\n")
            if player.queue:
                embed.description += "The queue has been cleared.\n"

            # Set player to default state
            player.loop = 0
            player.shuffle = False
            player.queue.clear()

            # Stop music, disconnect from voice channel and send response
            await player.stop()
            await interaction.guild.voice_client.disconnect(force=True)
            await interaction.response.send_message(embed=embed)

    # Cleaned
    @log_calls
    @catch_command_errors
    @nextcord.slash_command(description="Pause the current song.", guild_ids=tempo_guild_ids)
    async def pause(self, interaction: nextcord.Interaction):
        # Get player for current guild
        player = await self._get_player(interaction)

        # If Tempo is not connected to voice channel or not in same voice channel as user
        if not player or not await self._check_voice_state(interaction, player): return

        # If Tempo is not playing music
        elif not player.is_playing:
            embed = tempo_embed("No music is currently playing.")
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # If player is already paused
        elif player.paused:
            embed = tempo_embed("Music is already paused.")
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # Proceed with pause command
        else:
            await player.set_pause(True)
            embed = tempo_embed("Playback has been paused.\nUse `/resume` to continue playing.")
            await interaction.response.send_message(embed=embed)

    # Cleaned
    @log_calls
    @catch_command_errors
    @nextcord.slash_command(description="Resume the paused song.", guild_ids=tempo_guild_ids)
    async def resume(self, interaction: nextcord.Interaction):
        # Get player for current guild
        player = await self._get_player(interaction)

        # If Tempo is not connected to voice channel or not in same voice channel as user
        if not player or not await self._check_voice_state(interaction, player): return

        # If Tempo is not playing music
        elif not player.is_playing:
            embed = tempo_embed("No music is currently playing.")
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # If player is not paused
        elif not player.paused:
            embed = tempo_embed("Music is not paused.")
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # Proceed with resume command
        else:
            await player.set_pause(False)
            embed = tempo_embed("Playback has been resumed.")
            await interaction.response.send_message(embed=embed)

    # Cleaned
    @log_calls
    @catch_command_errors
    @nextcord.slash_command(description="Skip the current song.", guild_ids=tempo_guild_ids)
    async def skip(self, interaction: nextcord.Interaction):
        # Get player for current guild
        player = await self._get_player(interaction)

        # If Tempo is not connected to voice channel or not in same voice channel as user
        if not player or not await self._check_voice_state(interaction, player): return

        # If Tempo is not playing music
        elif not player.is_playing:
            embed = tempo_embed("No music is currently playing.")
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # If player is paused
        elif player.paused:
            embed = tempo_embed("Unable to skip while the player is paused.\nUse `/resume` to continue playing.")
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # If repeat (track) is enabled
        elif player.loop == 1:
            embed = tempo_embed("Unable to skip while loop mode is set to loop track.\nUse `/loop 0` to disable loop mode.\nUse `/loop 2` to loop queue.")
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # Proceed with skip command
        else:
            track = player.current
            embed = tempo_embed(f"Skipped: [{track['title']}]({track['uri']})")

            if player.queue:
                track = player.queue[0]
                embed.description += (f"\nNow Playing: [{track['title']}]({track['uri']})")

                if player.shuffle:
                    embed.description += "\n Shuffle is enabled. Use `/shuffle` to disable."   

            # Skip track and send response
            await player.skip()
            await interaction.response.send_message(embed=embed)

    # Cleaned
    @log_calls
    @catch_command_errors
    @nextcord.slash_command(description="Restart the current song.", guild_ids=tempo_guild_ids)
    async def restart(self, interaction: nextcord.Interaction):
        # Get player for guild from guild cache
        player = await self._get_player(interaction)

        # If Tempo is not connected to voice channel or not in same voice channel as user
        if not player or not await self._check_voice_state(interaction, player): return

        # If Tempo is not playing music
        elif not player.is_playing:
            embed = tempo_embed("No music is currently playing.")
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # If player is paused
        elif player.paused:
            embed = tempo_embed("Unable to restart while the player is paused.\nUse `/resume` to continue playing.")
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # Proceed with restart command
        else:
            track = player.current
            embed = tempo_embed(f"Restarted: [{track['title']}]({track['uri']})")

            # Restart track and send response
            await player.seek(0)
            await interaction.response.send_message(embed=embed)

    # Cleaned
    @log_calls
    @catch_command_errors
    @nextcord.slash_command(description="Seek to a specific position in the current song.", guild_ids=tempo_guild_ids)
    async def seek(self, interaction: nextcord.Interaction, position: int = nextcord.SlashOption(description="Time in seconds to seek to")):
        # Get player for guild from guild cache
        player = await self._get_player(interaction)

        # If Tempo is not connected to voice channel or not in same voice channel as user
        if not player or not await self._check_voice_state(interaction, player): return

        # If Tempo is not playing music
        elif not player.is_playing:
            embed = tempo_embed("No music is currently playing.")
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # If player is paused
        elif player.paused:
            embed = tempo_embed("Unable to seek while the player is paused.\nUse `/resume` to continue playing.")
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # Proceed with seek command
        else:
            # Convert track duration to seconds
            duration = math.floor(player.current.duration / 1000)

            # Validate user input
            if position < 0 or position > duration:
                embed = tempo_embed(f"Invalid position.\nTrack length: {duration} seconds.\nTry `/seek {duration // 2}` to jump halfway.")
                return await interaction.response.send_message(embed=embed, ephemeral=True)

            embed = tempo_embed(f"Seeking to {position} seconds.")

            # Seek to the specified position and send response
            await player.seek(position * 1000)
            await interaction.response.send_message(embed=embed)

    # Cleaned
    @log_calls
    @catch_command_errors
    @nextcord.slash_command(description="Get the title of the current song.", guild_ids=tempo_guild_ids)
    async def song(self, interaction: nextcord.Interaction):
        # Get player for guild from guild cache
        player = await self._get_player(interaction)

        # If Tempo is not connected to voice channel or not in same voice channel as user
        if not player or not await self._check_voice_state(interaction, player): return

        # If Tempo is not playing music
        elif not player.is_playing:
            embed = tempo_embed("No music is currently playing.")
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # Proceed with song command
        else:
            # Get current track, convert duration to seconds and send response
            track = player.current
            duration = math.floor(track.duration / 1000)
            embed = tempo_embed(f"Now Playing: [{track['title']}]({track['uri']})\nDuration: `{duration} seconds`")
            await interaction.response.send_message(embed=embed)

    # Cleaned
    @log_calls
    @catch_command_errors
    @nextcord.slash_command(description="Get a list of all songs in the queue.", guild_ids=tempo_guild_ids)
    async def queue(self, interaction: nextcord.Interaction):
        # Get player for guild from guild cache
        player = await self._get_player(interaction)

        # If Tempo is not connected to voice channel or not in same voice channel as user
        if not player or not await self._check_voice_state(interaction, player): return

        # If Tempo is not playing music
        elif not player.is_playing:
            embed = tempo_embed("No music is currently playing.")
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # If queue is empty
        elif not player.queue:
            embed = tempo_embed("The queue is empty.")
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Proceed with queue command
        else:
            # Create embed, add queued song titles and send response
            embed = tempo_embed("")
            embed.description = ""

            for index, track in enumerate(player.queue[:10]):  # Limit to first 10 tracks to prevent long messages
                embed.description += f"{index + 1}. [{track['title']}]({track['uri']})\n"

            await interaction.response.send_message(embed=embed)

    # Cleaned
    @log_calls
    @catch_command_errors
    @nextcord.slash_command(description="Check or change the playback volume.", guild_ids=tempo_guild_ids)
    async def volume(
        self, 
        interaction: nextcord.Interaction, 
        volume: int = nextcord.SlashOption(
            description="Set volume level from 1 to 100 (leave blank to check current volume)",
            required=False,
            min_value=1,
            max_value=100
        )
    ):
        # Get player for guild from guild cache
        player = await self._get_player(interaction)

        # Get server owner ID
        owner = interaction.guild.owner_id

        # If Tempo is not connected to voice channel or not in same voice channel as user
        if not player or not await self._check_voice_state(interaction, player): return

        # If Tempo is not playing music
        elif not player.is_playing:
            embed = tempo_embed("No music is currently playing.")
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # Proceed with volume command
        else:
            # If no volume is specified by user, return current volume
            if volume is None:
                embed = tempo_embed(f"Current volume: {player.volume}%")
                return await interaction.response.send_message(embed=embed)

            # Check if user has permission (server owner only)
            if interaction.user.id != owner:
                embed = tempo_embed("Only the server owner can adjust the volume.")
                return await interaction.response.send_message(embed=embed, ephemeral=True)

            # Get current volume and set new volume
            current_volume = player.volume
            await player.set_volume(volume)

            # Send response
            if volume > current_volume:
                embed = tempo_embed(f"Volume increased from {current_volume}% to {volume}%.")
            elif volume < current_volume:
                embed = tempo_embed(f"Volume decreased from {current_volume}% to {volume}%.")
            else:
                embed = tempo_embed(f"Volume is already set to {volume}%.")

            await interaction.response.send_message(embed=embed)

    # Cleaned
    @log_calls
    @catch_command_errors
    @nextcord.slash_command(description="Remove a song from the queue by its position.", guild_ids=tempo_guild_ids)
    async def remove(self, interaction: nextcord.Interaction, index: int = nextcord.SlashOption(description="Track number to remove from queue.")):
        # Get player for guild from guild cache
        player = await self._get_player(interaction)

        # If Tempo is not connected to voice channel or not in same voice channel as user
        if not player or not await self._check_voice_state(interaction, player): return

        # If queue is empty
        elif not player.queue:
            embed = tempo_embed("The queue is empty, nothing to remove.")
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # Validate user input
        elif index < 1 or index > len(player.queue):
            embed = tempo_embed(f"Invalid position.\nThe queue has {len(player.queue)} tracks.\nTry `/remove {len(player.queue)}` to remove the last song.")
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Proceed with remove command
        else:
            # Get track, remove track from queue and send response
            track = player.queue.pop(index - 1)
            embed = tempo_embed(f"Removed: [{track['title']}]({track['uri']})")
            await interaction.response.send_message(embed=embed)

    # Cleaned
    @log_calls
    @catch_command_errors
    @nextcord.slash_command(description="Set loop mode.", guild_ids=tempo_guild_ids)
    async def loop(
        self, 
        interaction: nextcord.Interaction , 
        mode: int = nextcord.SlashOption(
            description="Set loop mode (0: Loop disabled, 1: Loop track, 2: Loop queue)",
            required=True,
            min_value=0,
            max_value=2
        )
    ):
        # Get player for current guild
        player = await self._get_player(interaction)

        # If Tempo is not connected to voice channel or not in same voice channel as user
        if not player or not await self._check_voice_state(interaction, player): return

        # If Tempo is not playing music
        elif not player.is_playing:
            embed = tempo_embed("No music is currently playing.")
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # Proceed with loop command
        else:
            if mode == 0:
                embed = tempo_embed("Loop mode `disabled`")
            if mode == 1:
                embed = tempo_embed("Loop mode set to `loop track`")
            if mode == 2:
                embed = tempo_embed("Loop mode set to `loop queue`")

            # Set repeat mode and send response
            player.loop = mode
            await interaction.response.send_message(embed=embed)

    # Disabled (Temporarily)
    @log_calls
    @catch_command_errors
    @nextcord.slash_command(description="Toggle shuffle mode for the queue.", guild_ids=tempo_guild_ids)
    async def shuffle(self, interaction: nextcord.Interaction):
        # Get player for guild from guild cache
        player = self.bot.lavalink.player_manager.get(interaction.guild.id)

        # Create embed and set border color
        embed = tempo_embed()

        # If player does not exist or queue is empty
        if not player or not player.queue:
            embed.description = "The queue is empty, nothing to shuffle."
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # Toggle shuffle
        if player.shuffle:
            player.shuffle = not player.shuffle
        else:
            player.shuffle = True
        status = "enabled" if player.shuffle else "disabled"

        # Send response
        embed.description = f"Shuffle mode has been **{status}**."
        await interaction.response.send_message(embed=embed)

    @log_calls
    @developer_only
    @catch_command_errors
    @nextcord.slash_command(description="[Developer Only] Test multiple-track playback.", guild_ids=tempo_guild_ids)
    async def test(self, interaction: nextcord.Interaction):
        test_query = "https://www.youtube.com/playlist?list=PLkq4HKf72undqxj6cKoIE0Ur7970NFSi1"
        await self.play(interaction, test_query)

    @log_calls
    @developer_only
    @catch_command_errors
    @nextcord.slash_command(description="[Developer Only] Test single-track playback.", guild_ids=tempo_guild_ids)
    async def testsn(self, interaction: nextcord.Interaction):
        test_query = "fade oscuro"
        await self.play(interaction, test_query)


def setup(bot):
    bot.add_cog(Music(bot))