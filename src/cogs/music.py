import nextcord as nxt
from nextcord.ext import commands as cmd
from tokens import *
import lavalink
import asyncio
import random
import math
import re

class LavalinkVoiceClient(nxt.VoiceClient):
    def __init__(self, client: nxt.Client, channel: nxt.abc.Connectable):
        self.client = client
        self.channel = channel
        if hasattr(self.client, 'lavalink'):
            self.lavalink = self.client.lavalink
        else:
            self.client.lavalink = lavalink.Client(client.user.id)
            self.client.lavalink.add_node(node_host, node_port, node_password, node_region, node_name)  # Host, Port, Password, Region, Name
            self.lavalink = self.client.lavalink

    async def on_voice_server_update(self, data):
        # Convert data before sending to voice_update_handler
        lavalink_data = {
                't': 'VOICE_SERVER_UPDATE',
                'd': data
                }
        await self.lavalink.voice_update_handler(lavalink_data)

    async def on_voice_state_update(self, data):
        # Convert data before sending to voice_update_handler
        lavalink_data = {
                't': 'VOICE_STATE_UPDATE',
                'd': data
                }
        await self.lavalink.voice_update_handler(lavalink_data)

    async def connect(self, *, timeout: float, reconnect: bool) -> None:
        # Connect to voice channel and create a player_manager
        self.lavalink.player_manager.create(guild_id=self.channel.guild.id)
        await self.channel.guild.change_voice_state(channel=self.channel)

    async def disconnect(self, *, force: bool) -> None:
        # Disconnect, clean up running player and leave voice client
        player = self.lavalink.player_manager.get(self.channel.guild.id)

        if not force and not player.is_connected:
            return

        # None = disconnect
        await self.channel.guild.change_voice_state(channel=None)

        # Must manually change channel_id to None
        player.channel_id = None
        self.cleanup()

class TempoView(nxt.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout = 60)
        self.ctx = ctx
        self.message = None
        self.requester = ctx.author

    async def on_timeout(self):
        if self.message:
            for item in self.children:
                item.disabled = True
            await self.message.edit(view=self)

class Music(cmd.Cog):
    def __init__(self, bot):
        self.bot = bot

        if not hasattr(bot, 'lavalink'):
            bot.lavalink = lavalink.Client(bot.user.id)
            bot.lavalink.add_node(node_host, node_port, node_password, node_region, node_name)  # Host, Port, Password, Region, Name

            lavalink.add_event_hook(self.track_hook)

    def cog_unload(self):
        # remove registered event hooks
        self.bot.lavalink._event_hooks.clear()

    async def cog_before_invoke(self, ctx):
        # command before-invoke handler
        guild_check = ctx.guild is not None

        # ensure bot and user are in same voice channel.
        if guild_check:
            await self.ensure_voice(ctx)

        return guild_check

    async def cog_command_error(self, ctx, error):
        if isinstance(error, cmd.CommandInvokeError):
            embed = nxt.Embed(color=nxt.Color.from_rgb(134, 194, 50))
            if ctx.guild == None:
                embed.description = 'Unable to locate user/voice channel.'
                await ctx.send(embed = embed)
            else:
                # Log cog errors
                embed.description = error.original
                await ctx.send(embed = embed)

    # ensure bot and user are in same voice channel
    async def ensure_voice(self, ctx):
        # Returns player if one exists, otherwise creates. Ensures that a player always exists for guild
        player = self.bot.lavalink.player_manager.create(ctx.guild.id, endpoint=str(ctx.guild.region))
        
        # Commands that require the bot to join a voicechannel (i.e. initiating playback)
        should_connect = ctx.command.name in ('play', 'search')

        if not ctx.author.voice or not ctx.author.voice.channel:
            # cog_command_error handler catches this and sends it to the voicechannel
            raise cmd.CommandInvokeError('You must be in a voice channel to use this command.')

        if not player.is_connected:
            if not should_connect:
                raise cmd.CommandInvokeError('Tempo is not connected to a voice channel.')

            permissions = ctx.author.voice.channel.permissions_for(ctx.me)

            if not permissions.connect or not permissions.speak:  # Check user limit too?
                raise cmd.CommandInvokeError('Tempo needs `Connect` and `Speak` permissions.')

            player.store('channel', ctx.channel.id)
            await ctx.author.voice.channel.connect(cls=LavalinkVoiceClient)
        else:
            if int(player.channel_id) != ctx.author.voice.channel.id:
                raise cmd.CommandInvokeError('You must be in the same voice channel as Tempo to use this command.')

    # Automatically disconnect after period of inactivity
    async def disconnect_timer(self, guild, player, delay):
            timer = 0
            while True:
                # Sleep and increment timer
                await asyncio.sleep(1)
                timer += 1

                # If Tempo is not connected to a voice channel
                if not guild.voice_client: break

                # If Tempo is playing music
                if player.is_playing: break

                # If time limit is reached
                if timer == delay:
                    # Disable repeat and shuffle
                    player.set_repeat(False)
                    player.set_shuffle(False)
                    
                    # Clear queue
                    player.queue.clear()

                    # Stop player
                    await player.stop()

                    # Disconnect from voice channel
                    await guild.voice_client.disconnect(force=True)
                    break

    # Runs when the music stops
    async def track_hook(self, event):
        if isinstance(event, lavalink.events.QueueEndEvent):
            # When track_hook receives "QueueEndEvent" from lavalink.py
            guild_id = int(event.player.guild_id)
            guild = self.bot.get_guild(guild_id)
            player = event.player

            # Start disconnect timer
            timer = 0
            while True:
                # Sleep and increment timer
                await asyncio.sleep(1)
                timer += 1

                # If Tempo is not connected to a voice channel
                if not guild.voice_client: break

                # If Tempo is playing music
                if player.is_playing: break

                # If time limit is reached (90 seconds = 1.5 minutes)
                if timer == 90:
                    # Disable repeat and shuffle
                    player.set_repeat(False)
                    player.set_shuffle(False)
                    
                    # Clear queue
                    player.queue.clear()

                    # Stop player
                    await player.stop()

                    # Disconnect from voice channel
                    await guild.voice_client.disconnect(force=True)
                    break

    # When any user's voice state changes
    @cmd.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        # If voice state update is not Tempo
        if member.id != self.bot.user.id and member.guild.voice_client:
            # Get player for guild from guild cache
            player = self.bot.lavalink.player_manager.get(member.guild.id)

            # If user was in same channel as Tempo prior to voice state update
            if before.channel == member.guild.voice_client.channel and len(member.guild.voice_client.channel.members) == 1:
                # Start disconnect timer
                timer = 0
                while True:
                    # Sleep and increment timer
                    await asyncio.sleep(1)
                    timer += 1

                    # If Tempo is not connected to a voice channel
                    if not member.guild.voice_client: break

                    # If Tempo is no longer alone in voice channel, stop timer
                    if len(member.guild.voice_client.channel.members) > 1: break

                    # If time limit is reached (180 seconds = 3 minutes)
                    if timer == 180:
                        # Disable repeat and shuffle
                        player.set_repeat(False)
                        player.set_shuffle(False)
                        
                        # Clear queue
                        player.queue.clear()

                        # Stop player
                        await player.stop()

                        # Disconnect from voice channel
                        await member.guild.voice_client.disconnect(force=True)
                        break

    # Play a song or, if a song is already playing, add to the queue
    @cmd.command(aliases = ['p'])
    async def play(self, ctx, *, query: str = ''):
        # Get player for guild from guild cache
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        # Random number for hints message
        rand = int(random.random() * 100)

        # Create embed and set border color
        embed = nxt.Embed(color=nxt.Color.from_rgb(134, 194, 50))

        # 1% chance to send search hint message
        if rand == 1:
            embed.description = 'Did you know Tempo has search function? \n Try `!search <song title and artist>` to pick from a list of results.'
            await ctx.send(embed = embed)
            embed.description = ''

        # If user input invalid
        if query == '':
            # Send embed message
            embed.description = 'What song? Try `play <song title and artist>`.'
            return await ctx.send(embed = embed)

        # Suppress link embeds
        query = query.strip('<>')

        # Check if input is URL
        url_rx = re.compile(r'https?://(?:www\.)?.+')
        if url_rx.match(query):
            if 'soundcloud.com' in (query):
                embed.description = ('SoundCloud is currently disabled.')
                return await ctx.send(embed = embed)
        else:
            query = f'scsearch:{query}'

        # Get results for query from Lavalink
        results = await player.node.get_tracks(query)

        # If query returns no results
        if not results or not results['tracks']:
            # Disconnect if no audio is playing
            if not player.is_playing:
                await ctx.voice_client.disconnect(force=True)

            # Send embed message
            embed.description = 'No tracks found.'
            return await ctx.send(embed = embed)

        # If result is a playlist
        if results['loadType'] == 'PLAYLIST_LOADED':
            # Get tracklist from results
            tracks = results['tracks']

            # Add all tracks from playlist to queue
            for track in tracks:
                player.add(requester=ctx.author.id, track=track)

            # Embed message content
            if not player.is_playing:
                embed.description = 'Now Playing: ' + f'{results["playlistInfo"]["name"]} ({len(tracks)} tracks)'
            else:
                embed.description = 'Queued: ' + f'{results["playlistInfo"]["name"]} ({len(tracks)} tracks)'
        else:
            # Select track that isn't a music video if one exists, otherwise select first track in results
            excluded_phrases = ['music video', 'official video']
            if not url_rx.match(query):
                for result in results['tracks']:
                    if not any(phrase in result['info']['title'].lower() for phrase in excluded_phrases):
                        track = result
                        break
                    elif results['tracks'].index(result) == 9:
                        track = results['tracks'][0]
                        break
                        
            # Embed message content
            if not player.is_playing:
                embed.description = 'Now Playing: ' + f'[{track["info"]["title"]}]({track["info"]["uri"]})'
            else:
                embed.description ='Queued: ' + f'[{track["info"]["title"]}]({track["info"]["uri"]})'

            # Load track
            track = lavalink.models.AudioTrack(track, ctx.author.id, recommended=True)
            player.add(requester=ctx.author.id, track=track)

            # If Tempo is paused, alert user
            if player.paused and player.is_playing:
                embed.description += '\n Tempo is paused. Use the `resume` command to continue playing.'

            # If repeat is enabled, alert user
            if player.repeat and player.is_playing:
                embed.description += '\n Repeat is enabled. Use the `repeat` command to disable.'

            # If shuffle is enabled, alert user
            if player.shuffle and player.is_playing:
                embed.description += '\n Shuffle is enabled. Use the `shuffle` command to disable.'

            # Send embed message
            await ctx.send(embed = embed)

            # Play track and set initial volume
            if not player.is_playing:
                await player.play()
                await player.reset_equalizer()
                await player.set_volume(20)

    # Stop audio playback, clear queue and disconnect
    @cmd.command(aliases=['st'])
    async def stop(self, ctx):
        # Get player for guild from guild cache
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        # Create embed and set border color
        embed = nxt.Embed(color=nxt.Color.from_rgb(134, 194, 50))

        # If user is not in the same voice channel
        if not ctx.author.voice or (player.is_connected and ctx.author.voice.channel.id != int(player.channel_id)):
            embed.description = 'You must be in the same voice channel as Tempo to use this command.'
            return await ctx.send(embed = embed)

        # Disconnect message
        embed.description = 'Tempo has disconnected. \n'
        
        # If there are songs in queue alert user that queue has been cleared
        if len(player.queue) > 0:
            embed.description += 'The queue has been cleared. \n'

        # Disable repeat and shuffle
        player.set_repeat(False)
        player.set_shuffle(False)

        # Stop current track
        await player.stop()

        # Clear queue
        player.queue.clear()

        # Disconnect from voice channel
        await ctx.voice_client.disconnect(force=True)

        # Send embed message
        await ctx.send(embed = embed)

    # Pause audio playback
    @cmd.command(aliases=['ps'])
    async def pause(self, ctx):
        # Get player for guild from guild cache
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        # Get guild
        guild = ctx.guild

        # Create embed and set border color
        embed = nxt.Embed(color=nxt.Color.from_rgb(134, 194, 50))

        # If player is not active
        if not player.is_playing:
            # Send embed message
            embed.description = 'Unable to pause. \n' + 'No music playing.'
            return await ctx.send(embed = embed)

        # If player is paused
        if player.paused:
            # Send embed message
            embed.description = 'Unable to pause. \n' + 'Tempo is already paused.'
            return await ctx.send(embed = embed)

        # Pause
        await player.set_pause(True)

        # Send embed message
        embed.description = 'Tempo will disconnect if paused for 30 minutes. \n' + 'Use the `resume` command to continue playing.'
        await ctx.send(embed = embed)

        # Start disconnect timer
        timer = 0
        while True:
            # Sleep and increment timer
            await asyncio.sleep(1)
            timer += 1

            # If Tempo is not connected to a voice channel
            if not guild.voice_client: break

            # If Tempo is playing music
            if not player.paused: break

            # If time limit is reached (1800 seconds = 30 minutes)
            if timer == 1800:
                # Disable repeat and shuffle
                player.set_repeat(False)
                player.set_shuffle(False)
                
                # Clear queue
                player.queue.clear()

                # Stop player
                await player.stop()

                # Disconnect from voice channel
                await guild.voice_client.disconnect(force=True)
                break

    # Resume audio playback
    @cmd.command(aliases=['rs'])
    async def resume(self, ctx):
        # Get player for guild from guild cache
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        # Create embed and set border color
        embed = nxt.Embed(color=nxt.Color.from_rgb(134, 194, 50))

        # If player is not active
        if not player.is_playing:
            # Send embed message
            embed.description = 'Unable to resume. \n' + 'No music playing.'
            return await ctx.send(embed = embed)

        # If player not paused
        if not player.paused:
            # Send embed message
            embed.description = 'Unable to resume. \n' + 'Tempo is not paused.'
            return await ctx.send(embed = embed)
            
        # Resume
        await player.set_pause(False)

        # Send embed message
        track = player.current
        embed.description = f'Resumed: [{track["title"]}]({track["uri"]})'
        return await ctx.send(embed = embed)

    # Skip the current song
    @cmd.command(aliases=['sk'])
    async def skip(self, ctx):
        # Get player for guild from guild cache
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        # Create embed and set border color
        embed = nxt.Embed(color=nxt.Color.from_rgb(134, 194, 50))

        # If player not active
        if not player.is_playing:
            # Send embed message
            embed.description = 'Unable to skip. \n' + 'No music playing.'
            return await ctx.send(embed = embed)

        # If player is paused
        if player.paused:
            # Send embed message
            embed.description = 'Unable to skip while Tempo is paused. \n' + 'Use the `resume` command to continue playing.'
            return await ctx.send(embed = embed)

        # Initial embed message content
        if len(player.queue) > 0:
            track = player.queue[0]
            embed.description = f'Now Playing: [{track["title"]}]({track["uri"]})'
        else:
            track = player.current
            embed.description = f'Skipped: [{track["title"]}]({track["uri"]})'

        # If repeat is enabled, alert user
        if player.repeat and player.is_playing:
            embed.description += '\n Repeat is enabled. Use the `repeat` command to disable.'

        # If shuffle is enabled, alert user
        if player.shuffle and player.is_playing:
            embed.description += '\n Shuffle is enabled. Use the `shuffle` command to disable.'

        # Send embed message
        await ctx.send(embed = embed)

        # Skip
        await player.skip()

    # Return to the beginning of the current song
    @cmd.command(aliases=['re'])
    async def restart(self, ctx):
        # Get player for guild from guild cache
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        # Create embed and set border color
        embed = nxt.Embed(color=nxt.Color.from_rgb(134, 194, 50))

        # If player not active
        if not player.is_playing:
            # Send embed message
            embed.description = 'Unable to restart. \n' + 'No music playing.'
            return await ctx.send(embed = embed)

        # If player is paused
        if player.paused:
            # Send embed message
            embed.description = 'Unable to restart while Tempo is paused. \n' + 'Use the `resume` command to continue playing.'
            return await ctx.send(embed = embed)

        # Restart
        await player.seek(0)

        # Send embed message
        track = player.current
        embed.description = f'Now Playing: [{track["title"]}]({track["uri"]})'
        return await ctx.send(embed = embed)

    # Seek to specified positon in song
    @cmd.command(aliases=['se'])
    async def seek(self, ctx, position = ''):
        # Get player for guild from guild cache
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        # Create embed and set border color
        embed = nxt.Embed(color=nxt.Color.from_rgb(134, 194, 50))

        # If player is not active
        if not player.is_playing:
            # Send embed message
            embed.description = 'Unable to seek. \n' + 'No music playing.'
            return await ctx.send(embed = embed)

        # If player is paused
        if player.paused:
            # Send embed message
            embed.description = 'Unable to seek while Tempo is paused. \n' + 'Use the `resume` command to continue playing.'
            return await ctx.send(embed = embed)

        # If user input invalid
        if not position.isnumeric():
            # Send embed message
            embed.description = 'Invalid position. \n' + 'Try `seek 30` to jump to 30 seconds.'
            return await ctx.send(embed = embed)

        # Convert user input
        position = int(position)

        # Track duration
        duration = math.floor(player.current.duration / 1000)
        half_duration = math.floor(duration / 2)

        # Wait for track to buffer
        if player.position < (player.current.duration * 0.02):
            # Send embed message
            embed.description = 'Track loading... \n' + f'Try again in {math.ceil(((player.current.duration * 0.02) - player.position) / 1000)} seconds.'
            return await ctx.send(embed = embed)

        # If no user input
        if position == '':
            # Send embed message
            embed.description = f'Current track length: {duration} seconds \n' + f'Try `seek {half_duration}` to jump to {half_duration} seconds.'
            return await ctx.send(embed = embed)

        # If user input out of range
        if position < 0 or position * 1000 > player.current.duration:
            embed.description = f'Current track length: {duration} seconds \n' + f'Try `seek {half_duration}` to jump to {half_duration} seconds.'
            return await ctx.send(embed = embed)

        # Send embed message
        embed.description = f'Seeking to {position} seconds.'
        await ctx.send(embed = embed)

        # Seek
        position = int(position)
        await player.seek(position * 1000)

    # Get the title of the current song
    @cmd.command(aliases=['sn'])
    async def song(self, ctx):
        # Get player for guild from guild cache
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        # Create embed and set border color
        embed = nxt.Embed(color=nxt.Color.from_rgb(134, 194, 50))

        # If player is not active
        if not player.is_playing:
            # Send embed message
            embed.description = 'No music playing.'
            return await ctx.send(embed = embed)

        # Get current song title
        track = player.current

        # Send embed message
        embed.description = f'Now Playing: [{track["title"]}]({track["uri"]})'
        await ctx.send(embed = embed)

    # Get a list of all songs currently in the queue
    @cmd.command(aliases=['q'])
    async def queue(self, ctx):
        # Get player for guild from guild cache
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        # Create embed and set border color
        embed = nxt.Embed(color=nxt.Color.from_rgb(134, 194, 50))
        embed.description = ''

        # If player is not active
        if not player.is_playing:
            # Send embed message
            embed.description = 'No music playing.'
            return await ctx.send(embed = embed)

        # If queue is empty
        if len(player.queue) == 0:
            # Send embed message
            embed.description = 'The queue is empty.'
            return await ctx.send(embed = embed)

        # Get all queued song titles
        for track in player.queue:
            # If adding song title to list exceeds max embed message length, break
            if len(embed.description) + len(f'[{track["title"]}]({track["uri"]}) \n') > 4096:
                break
            # Add queued track to embed message content
            embed.description += f'{player.queue.index(track) + 1}. [{track["title"]}]({track["uri"]}) \n'

        # Send embed message
        await ctx.send(embed = embed)

    # Change audio playback volume
    @cmd.command(aliases=['v', 'vol'])
    async def volume(self, ctx, volume = ''):
        # Get player for guild from guild cache
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        # Create embed and set border color
        embed = nxt.Embed(color=nxt.Color.from_rgb(134, 194, 50))

        # Get admin ID
        owner = await self.bot.fetch_user(ctx.guild.owner_id)

        if volume == '':
            embed.description = f'Volume: {player.volume}%'
            return await ctx.send(embed = embed)

        # If user input invalid
        if not volume.isdigit() or int(volume) < 1 or int(volume) > 100:
            # Send embed message
            embed.description = 'Enter a value from 1 to 100. \n' + 'Try `volume` to check current volume. **[everyone]**\n' + 'Try `volume 25` to set volume to 25%. **[admin only]**' 
            return await ctx.send(embed = embed)
        
        # Check if user has privelege to use command (admin only)
        if ctx.author.id != owner.id:
            # Send embed message
            embed.description = 'Only the server owner can adjust volume.'
            return await ctx.send(embed = embed)

        # Get current volume and user input volume
        current_volume = player.volume
        volume = int(volume)

        # Set player volume
        await player.set_volume(volume)

        # If volume increased
        if volume > current_volume:
            embed.description = f'Volume increased from {current_volume}% to {volume}%.'
        # If volume decreased
        elif volume < current_volume: 
            embed.description = f'Volume decreased from {current_volume}% to {volume}%.'
        # If volume unchanged
        elif volume == current_volume:
            embed.description = f'Volume is already set to {current_volume}%'
        
        # Send embed message
        await ctx.send(embed = embed)

    # Turn repeat on or off
    @cmd.command(aliases=['rp'])
    async def repeat(self, ctx):
        # Get player for guild from guild cache
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        # Create embed and set border color
        embed = nxt.Embed(color=nxt.Color.from_rgb(134, 194, 50))

        # Toggle repeat
        if player.repeat:
            # Disabled repeat
            player.set_repeat(False)

            # Send embed message
            embed.description = 'Repeat disabled.'
            await ctx.send(embed = embed)
        else:
            # Enable repeat
            player.set_repeat(True)
            
            # Send embed message
            embed.description = 'Repeat enabled.'
            await ctx.send(embed = embed)

    # Turn shuffle on or off
    @cmd.command(aliases=['sh'])
    async def shuffle(self, ctx):
        # Get player for guild from guild cache
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        # Create embed and set border color
        embed = nxt.Embed(color=nxt.Color.from_rgb(134, 194, 50))

        # Toggle shuffle
        if player.shuffle:
            # Disable shuffle
            player.set_shuffle(False)

            # Send embed message
            embed.description = 'Shuffle disabled.'
            await ctx.send(embed = embed)
        else:
            # Enable shuffle
            player.set_shuffle(True)

            # Send embed message
            embed.description = 'Shuffle enabled.'
            await ctx.send(embed = embed)

    # Remove a song from the queue
    @cmd.command(aliases=['rm'])
    async def remove(self, ctx, index = ''):
        # Get player for guild from guild cache
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        # Create embed and set border color
        embed = nxt.Embed(color=nxt.Color.from_rgb(134, 194, 50))

        # If player is not active
        if not player.is_playing:
            # Send embed message
            embed.description = 'No music playing.'
            return await ctx.send(embed = embed)

        # If queue is empty
        if len(player.queue) == 0:
            # Send embed message
            embed.description = 'The queue is empty.'
            return await ctx.send(embed = embed)

        # If user input invalid
        if index == '' or not index.isnumeric() or int(index) < 1 or int(index) > len(player.queue):
            # Send embed message
            embed.description = f'Try `rm {len(player.queue)}` to remove track number {len(player.queue)} from the queue.'
            return await ctx.send(embed = embed)

        # Get track from queue
        track = player.queue[int(index) - 1]

        # Embed message content
        embed.description = f'Removed: [{track["title"]}]({track["uri"]})'

        # Remove track
        del player.queue[int(index) - 1]

        # Send embed message
        await ctx.send(embed = embed)

    # Get a list of songs and choose which one to play
    @cmd.command(aliases=['sr'])
    async def search(self, ctx, *, query: str):
        # Get player for guild from guild cache
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        # Get guild
        guild = ctx.guild

        # Remove leading and trailing <>. <> suppress embedding links.
        query = query.strip('<>')

        # Search for given query, get results
        query = f'scsearch:{query}'
        results = await player.node.get_tracks(query)

        # When a button is clicked
        async def track_select(interaction):
            # If user interacting is not the user requesting
            if interaction.user != view.requester:
                return

            # Delete message containing buttons
            view.message = None
            await interaction.response.edit_message(view = view)
            await interaction.delete_original_message()

            # ID of which button was clicked
            track_number = int(interaction.data['custom_id'])

            # If user clicked a track
            track = results['tracks'][track_number]

            # Create embed and set border color
            embed = nxt.Embed(color=nxt.Color.from_rgb(134, 194, 50))

            # Add announcement to embed
            if not player.is_playing:
                embed.description = 'Now Playing: '
            else:
                embed.description ='Queued: '

            # Add track title to embed
            embed.description += f'[{track["info"]["title"]}]({track["info"]["uri"]})'

            # Add track to player
            player.add(requester=interaction.user, track=track)

            # Send embed message
            await interaction.channel.send(embed = embed)

            # Play track and set initial volume
            if not player.is_playing:
                await player.play()
                await player.set_volume(20)

        # Create view and add buttons for each track
        view = TempoView(ctx)
        for track in results['tracks'][0:5]:
            track_number = results['tracks'].index(track)
            track_button = nxt.ui.Button(
                label = track['info']['title'][0:80], 
                custom_id = str(track_number), 
                row = track_number, 
                style = nxt.ButtonStyle.grey
            )
            # Set callback
            track_button.callback = track_select

            # Add button to view
            view.add_item(track_button)

        # Send view and save as message
        message = await ctx.send(view = view)
        view.message = message

        # Start disconnect timer.
        timer = 0
        while True:
            # Sleep and increment timer
            await asyncio.sleep(1)
            timer += 1

            # If Tempo is not connected to a voice channel
            if not guild.voice_client: break

            # If Tempo is playing music
            if player.is_playing: break

            # If time limit is reached (90 seconds = 1.5 minutes)
            if timer == 90:
                # Disable repeat and shuffle
                player.set_repeat(False)
                player.set_shuffle(False)
                
                # Clear queue
                player.queue.clear()

                # Stop player
                await player.stop()

                # Disconnect from voice channel
                await guild.voice_client.disconnect(force=True)
                break

    # # Choose from a list of equalizer presets for a unique listening experience
    # @cmd.command(aliases=['eq'])
    # async def equalizer(self, ctx):
    #     # Get player for guild from guild cache
    #     player = self.bot.lavalink.player_manager.get(ctx.guild.id)

    #     # Create embed and set border color
    #     embed = nxt.Embed(color=nxt.Color.from_rgb(134, 194, 50))

    #     # Get admin ID
    #     owner = await self.bot.fetch_user(ctx.guild.owner_id)

    #     # Check if user has privelege to use command (admin only)
    #     if ctx.author.id != owner.id:
    #         # Send embed message
    #         embed.description = 'Only the server admin has access to the `equalizer` command.'
    #         return await ctx.send(embed = embed)

    #     # [(0, 25hz), (1, 40hz), (2, 63hz), (3, 100hz), (4, 160hz), (5, 250hz), (6, 400hz), (7, 630hz), (8, 1khz), (9, 1.6khz), (10, 2.5khz), (11, 4khz), (12, 6.3khz), (13, 10khz), (14, 16khz)]
    #     gains = [
    #         # Bass Boost
    #         [(0, 0), (1, 0), (2, 0.1), (3, 0.1), (4, 0.1), (5, 0.1), (6, 0), (7, 0), (8, 0), (9, 0), (10, 0), (11, 0), (12, 0), (13, 0), (14, 0)],
    #         # Mid Boost
    #         [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (5, 0), (6, 0), (7, 0.1), (8, 0.1), (9, 0.1), (10, 0.1), (11, 0), (12, 0), (13, 0), (14, 0)],
    #         # Treble Boost
    #         [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (5, 0), (6, 0), (7, 0), (8, 0), (9, 0), (10, 0), (11, 0), (12, 0.1), (13, 0.1), (14, 0.1)],
    #         # Old Radio
    #         [(0, -0.25), (1, -0.25), (2, -0.25), (3, -0.25), (4, -0.25), (5, -0.25), (6, -0.25), (7, -0.25), (8, -0.25), (9, -0.25), (10, 1), (11, -0.25), (12, -0.25), (13, -0.25), (14, -0.25)]
    #         ]

    #     # Reset player to default
    #     await player.reset_equalizer()

    #     # Applies a preset based on which button user clicks
    #     async def select_preset(interaction, gains = gains):
    #         # Delete message containing buttons
    #         view.message = None
    #         await interaction.response.edit_message(view = view)
    #         await interaction.delete_original_message()

    #         # Activate preset
    #         preset = interaction.data['custom_id']
    #         if preset == 'Bass Boost':
    #             await player.set_gains(*gains[0])
    #         elif preset == 'Mid Boost':
    #             await player.set_gains(*gains[1])
    #         elif preset == 'Treble Boost':
    #             await player.set_gains(*gains[2])
    #         elif preset == 'Lounge':
    #             await player.set_gains(*gains[3])

    #         embed.description = f'Applying: {preset}\nPlease wait...'
    #         await ctx.send(embed = embed)

    #     # Create view
    #     view = TempoView(ctx)

    #     # Create default preset button
    #     default_button = nxt.ui.Button(label = 'Default', custom_id = 'Default', style = nxt.ButtonStyle.grey)
    #     default_button.callback = select_preset
    #     view.add_item(default_button)

    #     # Create bass boost preset button
    #     bass_boost_button = nxt.ui.Button(label = 'Bass Boost', custom_id = 'Bass Boost', style = nxt.ButtonStyle.grey)
    #     bass_boost_button.callback = select_preset
    #     view.add_item(bass_boost_button)

    #     # Create treble boost preset button
    #     mid_boost_button = nxt.ui.Button(label = 'Mid Boost', custom_id = 'Mid Boost', style = nxt.ButtonStyle.grey)
    #     mid_boost_button.callback = select_preset
    #     view.add_item(mid_boost_button)


    #     # Create balanced boost preset button
    #     treble_boost_button = nxt.ui.Button(label = 'Treble Boost', custom_id = 'Treble Boost', style = nxt.ButtonStyle.grey)
    #     treble_boost_button.callback = select_preset
    #     view.add_item(treble_boost_button)

    #     # Create old radio preset button
    #     old_radio_button = nxt.ui.Button(label = 'Lounge', custom_id = 'Lounge', style = nxt.ButtonStyle.grey)
    #     old_radio_button.callback = select_preset
    #     view.add_item(old_radio_button)
        
    #     message = await ctx.send(view = view)
    #     view.message = message

# Add cog
def setup(bot):
    bot.add_cog(Music(bot))