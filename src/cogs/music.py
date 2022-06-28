import nextcord as nxt
from nextcord.ext import commands as cmd
from tokens import *
import lavalink
import asyncio
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
            self.client.lavalink.add_node(node_host, node_port, node_password, node_region, node_name)
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
        should_connect = ctx.command.name in ('play')

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

        # Create embed and set border color
        embed = nxt.Embed(color=nxt.Color.from_rgb(134, 194, 50))

        current_query = query

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
                embed.description = ('SoundCloud is currently unsupported.')
                return await ctx.send(embed = embed)
        else:
            query = f'ytsearch:{query}'

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

        # Skip
        await player.skip()

        # Embed message content
        if player.is_playing:
            track = player.current
            embed.description = 'Now Playing: ' + f'[{track["title"]}]({track["uri"]})'

        # If repeat is enabled, alert user
        if player.repeat and player.is_playing:
            embed.description += '\n Repeat is enabled. Use the `repeat` command to disable.'

        # If shuffle is enabled, alert user
        if player.shuffle and player.is_playing:
            embed.description += '\n Shuffle is enabled. Use the `shuffle` command to disable.'

        # Send embed message
        await ctx.send(embed = embed)

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

        # Check if user has privelege to use command (admin only)
        if ctx.author.id != owner.id:
            # Send embed message
            embed.description = 'Only the server admin has access to the `volume` command.'
            return await ctx.send(embed = embed)

        # If user input invalid
        if not volume.isdigit() or int(volume) < 1 or int(volume) > 100:
            # Send embed message
            embed.description = 'Enter a value from 1 to 100. \n' + 'Try `volume 25` to set volume to 25%.'
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

    # Choose from a list of equalizer presets for a more personalized listening experience
    # @cmd.command(aliases=['eq'])
    # async def equalizer(self, ctx, preset):
    #     # Get player for guild from guild cache
    #     player = self.bot.lavalink.player_manager.get(ctx.guild.id)

    #     # Create embed and set border color
    #     embed = nxt.Embed(color=nxt.Color.from_rgb(134, 194, 50))

    #     if preset == 'default':
    #         await player.reset_equalizer()

    #     if preset == 'bass':
    #         await player.set_gain(0, 1)
    #         await player.set_gain(1, 0)
    #         await player.set_gain(2, 0)
    #         await player.set_gain(3, 0)
    #         await player.set_gain(4, 0)
    #         await player.set_gain(5, 0)
    #         await player.set_gain(6, 0)
    #         await player.set_gain(7, 0)
    #         await player.set_gain(8, 0)
    #         await player.set_gain(9, 0)
    #         await player.set_gain(10, 1)
    #         await player.set_gain(11, 0)
    #         await player.set_gain(12, 0)
    #         await player.set_gain(13, 0)
    #         await player.set_gain(14, 0)

    #     if preset == 'clean':
    #         bands = [(0,1,2,3,4,5,6,7,8,9,10,11,12,13,14)]
    #         await player.set_gains(bands)

# Add cog
def setup(bot):
    bot.add_cog(Music(bot))