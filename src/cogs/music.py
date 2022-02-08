from discord.ext import commands
import discord
import lavalink
import re

url_rx = re.compile(r'https?://(?:www\.)?.+')


class LavalinkVoiceClient(discord.VoiceClient):
    def __init__(self, client: discord.Client, channel: discord.abc.Connectable):
        self.client = client
        self.channel = channel
        if hasattr(self.client, 'lavalink'):
            self.lavalink = self.client.lavalink
        else:
            self.client.lavalink = lavalink.Client(client.user.id)
            self.client.lavalink.add_node('localhost', 7000, 'sourceflow', 'na', 'default-node')
            self.lavalink = self.client.lavalink

    async def on_voice_server_update(self, data):
        # convert data before sending to voice_update_handler
        lavalink_data = {
                't': 'VOICE_SERVER_UPDATE',
                'd': data
                }
        await self.lavalink.voice_update_handler(lavalink_data)

    async def on_voice_state_update(self, data):
        # convert data before sending to voice_update_handler
        lavalink_data = {
                't': 'VOICE_STATE_UPDATE',
                'd': data
                }
        await self.lavalink.voice_update_handler(lavalink_data)

    async def connect(self, *, timeout: float, reconnect: bool) -> None:
        """ Connect to voice channel and create a player_manager. """
        self.lavalink.player_manager.create(guild_id=self.channel.guild.id)
        await self.channel.guild.change_voice_state(channel=self.channel)

    async def disconnect(self, *, force: bool) -> None:
        """ Disconnect, clean up running player and leave voice client. """
        player = self.lavalink.player_manager.get(self.channel.guild.id)

        if not force and not player.is_connected:
            return

        # None = disconnect
        await self.channel.guild.change_voice_state(channel=None)

        # Must manually change channel_id to None. 
        player.channel_id = None
        self.cleanup()


class Text(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['HELP'])
    async def help(self, ctx):
        """ Show command list in text channel. """
        help_menu = discord.Embed(color=discord.Color.from_rgb(134, 194, 50))
        help_menu.description = (
            '**[!p] !play <song name, artist>** \n' +
            '— play a song or add to queue \n' +
            # '**!next <song name, artist>** \n' +
            # '— play after current song (first in queue) \n' +
            # '**!song** \n' +
            # '— show current track info \n' +
            '**[!sk] !skip** \n' +
            '— skip to next track in queue \n' +
            '**[!st] !stop** \n' +
            '— stop playback and clear queue \n' +
            # '**!pause** \n' +
            # '— pause playback \n' +
            # '**!resume** \n' +
            # '— unpause playback \n' +
            '**[!fw] !forward <seconds>** \n' +
            '— skip forward given number of seconds \n' +
            '**[!bw] !backward <seconds>** \n' +
            '— skip backward given number of seconds \n' +
            '**[!rs] !restart** \n' +
            '— return to beginning of current track \n' +
            '**[!q] !queue** \n' +
            '— show active queue in text channel. \n' +
            '\n __**Tempo v2.1.1**__' + 
            '\n __**Developed by Hexxzn**__'
        )
        await ctx.channel.send(embed=help_menu)


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        if not hasattr(bot, 'lavalink'):
            bot.lavalink = lavalink.Client(bot.user.id)
            bot.lavalink.add_node('localhost', 7000, 'sourceflow', 'na', 'default-node')  # Host, Port, Password, Region, Name

        lavalink.add_event_hook(self.track_hook)

    def cog_unload(self):
        """ Remove registered event hooks. """
        self.bot.lavalink._event_hooks.clear()

    async def cog_before_invoke(self, ctx):
        """ Command before-invoke handler. """
        guild_check = ctx.guild is not None

        if guild_check:
            await self.ensure_voice(ctx)
            #  ensure bot and user are in same voice channel.

        return guild_check

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            await ctx.send(error.original)
            # Log cog errors

    async def ensure_voice(self, ctx):
        """ Ensure bot and user are in same voice channel. """
        # Returns player if one exists, otherwise creates. Ensures that a player always exists for guild.
        player = self.bot.lavalink.player_manager.create(ctx.guild.id, endpoint=str(ctx.guild.region))
        
        # Commands that require the bot to join a voicechannel (i.e. initiating playback).
        should_connect = ctx.command.name in ('play')

        if not ctx.author.voice or not ctx.author.voice.channel:
            # cog_command_error handler catches this and sends it to the voicechannel.
            raise commands.CommandInvokeError('You must be in a voice channel to use this command.')

        if not player.is_connected:
            if not should_connect:
                raise commands.CommandInvokeError('Tempo is not connected to a voice channel.')

            permissions = ctx.author.voice.channel.permissions_for(ctx.me)

            if not permissions.connect or not permissions.speak:  # Check user limit too?
                raise commands.CommandInvokeError('Bot needs `CONNECT` and `SPEAK` permissions.')

            player.store('channel', ctx.channel.id)
            await ctx.author.voice.channel.connect(cls=LavalinkVoiceClient)
        else:
            if int(player.channel_id) != ctx.author.voice.channel.id:
                raise commands.CommandInvokeError('You must be in the same voice channel as Tempo to use this command.')

    async def track_hook(self, event):
        if isinstance(event, lavalink.events.QueueEndEvent):
            # When track_hook receives "QueueEndEvent" from lavalink.py
            guild_id = int(event.player.guild_id)
            guild = self.bot.get_guild(guild_id)
            await guild.voice_client.disconnect(force=True)

    @commands.command(aliases=['PLAY', 'P', 'p'])
    async def play(self, ctx, *, query: str):
        """ Searches and plays a song from a given query. """
        # Get player for guild from cache.
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        # Set player volume.
        await player.set_volume(15)
        # Remove leading and trailing <>. <> suppress embedding links.
        query = query.strip('<>')

        # Check if input is URL. If not, YouTube search.
        if not url_rx.match(query):
            query = f'ytsearch:{query}'

        # Get results for query from Lavalink.
        results = await player.node.get_tracks(query)

        # Results could be None if Lavalink returns invalid response (non-JSON/non-200 (OK)).
        # Results['tracks'] could be empty array if query yields no tracks.
        if not results or not results['tracks']:
            return await ctx.send('No results.')

        embed = discord.Embed(color=discord.Color.from_rgb(134, 194, 50))

        # Valid loadTypes:
        #   TRACK_LOADED    - single video/direct URL
        #   PLAYLIST_LOADED - direct URL to playlist
        #   SEARCH_RESULT   - query prefixed with either ytsearch: or scsearch:
        #   NO_MATCHES      - query yielded no results
        #   LOAD_FAILED     - most likely, the video encountered an exception during loading
        if results['loadType'] == 'PLAYLIST_LOADED':
            tracks = results['tracks']

            for track in tracks:
                # Add all tracks from playlist to queue.
                player.add(requester=ctx.author.id, track=track)

            embed.description = f'{results["playlistInfo"]["name"]} - {len(tracks)} tracks'
        else:
            track = results['tracks'][0]

            if player.is_playing:
                embed.description = 'Queued: '
            else:
                embed.description ='Now Playing: '

            embed.description += f'[{track["info"]["title"]}]({track["info"]["uri"]})'

            track = lavalink.models.AudioTrack(track, ctx.author.id, recommended=True)
            player.add(requester=ctx.author.id, track=track)

        await ctx.send(embed=embed)

        if not player.is_playing:
            await player.play()

    @commands.command(aliases=['STOP', 'ST', 'st'])
    async def stop(self, ctx):
        """ Disconnects player from voice channel and clears queue. """
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        if not player.is_connected:
            return await ctx.send('Tempo is not connected to a voice channel.')

        if not ctx.author.voice or (player.is_connected and ctx.author.voice.channel.id != int(player.channel_id)):
            return await ctx.send('You must be in the same voice channel as Tempo to use this command.')

        # Clear queue.
        player.queue.clear()
        # Stop current track.
        await player.stop()
        # Disconnect from voice channel.
        await ctx.voice_client.disconnect(force=True)
        await ctx.send('Queue has been cleared.')

    @commands.command(aliases=['SKIP', 'SK', 'sk'])
    async def skip(self, ctx):
        """ Skips to next track in queue. """
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        await player.skip()

    @commands.command(aliases=['FORWARD', 'FW', 'fw'])
    async def forward(self, ctx, seconds = None):
        """ Fast forwards given number of seconds. """
        if seconds == None:
            return await ctx.send('How far? Try __**!forward 15**__ or __**!fw 15**__ to skip forward 15 seconds.')
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        await player.seek(player.position + int(seconds) * 1000)

    @commands.command(aliases=['BACKWARD', 'BW', 'bw'])
    async def backward(self, ctx, seconds = None):
        """ Rewinds given number of seconds. """
        if seconds == None:
            return await ctx.send('How far? Try __**!backward 15**__ or __**!bw 15**__ to skip backward 15 seconds.')
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        await player.seek(player.position - int(seconds) * 1000)

    @commands.command(aliases=['RESTART', 'RS', 'rs'])
    async def restart(self, ctx):
        """ Returns to beginning of current track. """
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        await player.seek(player.position - player.position)

    @commands.command(aliases=['QUEUE', 'Q', 'q'])
    async def queue(self, ctx):
        """ Show current queue in text channel. """
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        embed = discord.Embed(color=discord.Color.from_rgb(134, 194, 50))
        embed.description = 'Queue Empty'
        if len(player.queue) > 0:
            embed.description = 'Next: '
            for track in player.queue:
                embed.description += f'[{track["title"]}]({track["uri"]}) \n'

        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(Text(bot))
    bot.add_cog(Music(bot))