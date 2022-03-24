from discord.ext import commands
import lavalink
import discord
import asyncio
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
        """ connect to voice channel and create a player_manager """
        self.lavalink.player_manager.create(guild_id=self.channel.guild.id)
        await self.channel.guild.change_voice_state(channel=self.channel)

    async def disconnect(self, *, force: bool) -> None:
        """ disconnect, clean up running player and leave voice client """
        player = self.lavalink.player_manager.get(self.channel.guild.id)

        if not force and not player.is_connected:
            return

        # None = disconnect
        await self.channel.guild.change_voice_state(channel=None)

        # Must manually change channel_id to None. 
        player.channel_id = None
        self.cleanup()


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        if not hasattr(bot, 'lavalink'):
            bot.lavalink = lavalink.Client(bot.user.id)
            bot.lavalink.add_node('localhost', 7000, 'sourceflow', 'na', 'default-node')  # Host, Port, Password, Region, Name

            lavalink.add_event_hook(self.track_hook)

    def cog_unload(self):
        """ remove registered event hooks """
        self.bot.lavalink._event_hooks.clear()

    async def cog_before_invoke(self, ctx):
        """ command before-invoke handler """
        guild_check = ctx.guild is not None

        if guild_check:
            await self.ensure_voice(ctx)
            #  ensure bot and user are in same voice channel.

        return guild_check

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            embed = discord.Embed(color=discord.Color.from_rgb(134, 194, 50))
            if ctx.guild == None:
                embed.description = 'Unable to locate user/voice channel.'
                await ctx.send(embed = embed)
            else:
                # Log cog errors
                embed.description = error.original
                await ctx.send(embed = embed)

    async def ensure_voice(self, ctx):
        """ ensure bot and user are in same voice channel """
        # Returns player if one exists, otherwise creates. Ensures that a player always exists for guild.
        player = self.bot.lavalink.player_manager.create(ctx.guild.id, endpoint=str(ctx.guild.region))
        
        # Commands that require the bot to join a voicechannel (i.e. initiating playback).
        should_connect = ctx.command.name in ('play', 'search')

        if not ctx.author.voice or not ctx.author.voice.channel:
            # cog_command_error handler catches this and sends it to the voicechannel.
            raise commands.CommandInvokeError('You must be in a voice channel to use this command.')

        if not player.is_connected:
            if not should_connect:
                raise commands.CommandInvokeError('Tempo is not connected to a voice channel.')

            permissions = ctx.author.voice.channel.permissions_for(ctx.me)

            if not permissions.connect or not permissions.speak:  # Check user limit too?
                raise commands.CommandInvokeError('Tempo needs `CONNECT` and `SPEAK` permissions.')

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
            player = event.player

            # Start disconnect timer.
            time = 0
            while True:
                await asyncio.sleep(1)
                time += 1
                if not guild.voice_client:
                    break
                if player.is_playing:
                    break
                if time == 90:
                    player.queue.clear()
                    await player.stop()
                    await guild.voice_client.disconnect(force=True)
                    break

    @commands.command(aliases=['p'])
    async def play(self, ctx, *, query: str):
        """ play song or add to queue """
        # Get player for guild from cache.
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        # Set player volume.
        await player.set_volume(17)
        # Remove leading and trailing <>. <> suppress embedding links.
        query = query.strip('<>')

        # Check if input is URL. If not, YouTube search.
        if not url_rx.match(query):
            query = f'ytsearch:{query}'

        # Get results for query from Lavalink.
        results = await player.node.get_tracks(query)

        embed = discord.Embed(color=discord.Color.from_rgb(134, 194, 50))

        # Results could be None if Lavalink returns invalid response (non-JSON/non-200 (OK)).
        # Results['tracks'] could be empty array if query yields no tracks.
        if not results or not results['tracks']:
            if not player.is_playing:
                await ctx.voice_client.disconnect(force=True)
            embed.description = 'No tracks found.'
            return await ctx.send(embed = embed)

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

            if not player.is_playing:
                embed.description = 'Now Playing: ' + f'{results["playlistInfo"]["name"]} ({len(tracks)} tracks)'
            else:
                embed.description = 'Queued: ' + f'{results["playlistInfo"]["name"]} ({len(tracks)} tracks)'
        else:
            index = 0
            # To avoid music videos with extended intros, skits etc.
            exclude = ['music video', 'official video']
            if not url_rx.match(query):
                while index <= 5:
                    for string in exclude:
                        if string in results['tracks'][index]['info']['title'].lower():
                            index += 1
                            break
                    else:
                        break
                else:
                    index = 0

            track = results['tracks'][index]

            if not player.is_playing:
                embed.description = 'Now Playing: '
            else:
                embed.description ='Queued: '

            embed.description += f'[{track["info"]["title"]}]({track["info"]["uri"]})'

            track = lavalink.models.AudioTrack(track, ctx.author.id, recommended=True)
            player.add(requester=ctx.author.id, track=track)

        await ctx.send(embed = embed)

        if not player.is_playing:
            await player.play()

    # @commands.command(aliases=['se'])
    # async def search(self, ctx, *, query: str):
    #     # Get player for guild from cache.
    #     player = self.bot.lavalink.player_manager.get(ctx.guild.id)
    #     # Set player volume.
    #     await player.set_volume(17)
    #     # Remove leading and trailing <>. <> suppress embedding links.
    #     query = query.strip('<>')
    #     # Search YouTube for given query
    #     query = f'ytsearch:{query}'
    #     results = await player.node.get_tracks(query)
    #     embed = discord.Embed(color=discord.Color.from_rgb(134, 194, 50))

    #     embed.description = '__**Results**__' + '\n \n'
    #     count = 1
    #     for track in results['tracks']:
    #         embed.description += f'{count}. [{track["info"]["title"]}]({track["info"]["uri"]}) \n'
    #         count += 1
    #         if count > 10:
    #             break

    #     await ctx.send(embed = embed)

    #     # Start disconnect timer.
    #     time = 0
    #     while True:
    #         await asyncio.sleep(1)
    #         time += 1
    #         if not ctx.guild.voice_client:
    #             break
    #         if player.is_playing:
    #             break
    #         if time == 90:
    #             player.queue.clear()
    #             await player.stop()
    #             await ctx.guild.voice_client.disconnect(force=True)
    #             break

    @commands.command(aliases=['st'])
    async def stop(self, ctx):
        """ stop playback and clear queue """
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        embed = discord.Embed(color=discord.Color.from_rgb(134, 194, 50))

        if not player.is_connected:
            embed.description = 'Tempo is not connected to a voice channel.'
            return await ctx.send(embed = embed)

        if not ctx.author.voice or (player.is_connected and ctx.author.voice.channel.id != int(player.channel_id)):
            embed.description = 'You must be in the same voice channel as Tempo to use this command.'
            return await ctx.send(embed = embed)

        # Clear queue.
        player.queue.clear()
        # Stop current track.
        await player.stop()
        # Disconnect from voice channel.
        await ctx.voice_client.disconnect(force=True)
        embed.description = 'Queue has been cleared.'
        await ctx.send(embed = embed)

    @commands.command(aliases=['ps'])
    async def pause(self, ctx):
        """ pause playback """
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        await player.set_pause(True)
        embed = discord.Embed(color=discord.Color.from_rgb(134, 194, 50))
        embed.description = 'Tempo will disconnect if paused for 30 minutes. Use `!resume` to continue playing.'
        await ctx.send(embed = embed)

        # Start disconnect timer.
        time = 0
        while True:
            await asyncio.sleep(1)
            time += 1
            if not ctx.guild.voice_client:
                break
            if player.paused == False:
                break
            if time == 1800:
                player = self.bot.lavalink.player_manager.get(ctx.guild.id)
                player.queue.clear()
                await player.stop()
                await ctx.guild.voice_client.disconnect(force=True)
                break

    @commands.command(aliases=['rs'])
    async def resume(self, ctx):
        """ unpause playback """
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        await player.set_pause(False)

    @commands.command(aliases=['sk'])
    async def skip(self, ctx):
        """ skip to next track in queue """
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        await player.skip()

    @commands.command(aliases=['fw'])
    async def forward(self, ctx, seconds = None):
        """ skip forward given number of seconds """
        if seconds == None:
            embed = discord.Embed(color=discord.Color.from_rgb(134, 194, 50))
            embed.description = 'How far? Try `!forward 15` to skip forward 15 seconds.'
            return await ctx.send(embed = embed)
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        await player.seek(player.position + int(seconds) * 1000)

    @commands.command(aliases=['bw'])
    async def backward(self, ctx, seconds = None):
        """ skip backward given number of seconds """
        if seconds == None:
            embed = discord.Embed(color=discord.Color.from_rgb(134, 194, 50))
            embed.description = 'How far? Try `!backward 15` to skip backward 15 seconds.'
            return await ctx.send(embed = embed)
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        await player.seek(player.position - int(seconds) * 1000)

    @commands.command(aliases=['re'])
    async def restart(self, ctx):
        """ returns to beginning of current track """
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        await player.seek(player.position - player.position)

    @commands.command(aliases=['q'])
    async def queue(self, ctx):
        """ show active queue in text channel """
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        embed = discord.Embed(color=discord.Color.from_rgb(134, 194, 50))
        embed.description = 'Queue Empty'
        if len(player.queue) > 0:
            track = player.current
            embed.description = f'Now Playing: [{track["title"]}]({track["uri"]}) \n Next: '
            for track in player.queue:
                if len(embed.description) + len(f'[{track["title"]}]({track["uri"]}) \n') > 4096:
                    break
                embed.description += f'[{track["title"]}]({track["uri"]}) \n'
        await ctx.send(embed = embed)

    @commands.command(aliases=['sn'])
    async def song(self, ctx):
        """ show current track in text channel """
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        embed = discord.Embed(color=discord.Color.from_rgb(134, 194, 50))
        if player.is_playing:
            track = player.current
            embed.description = f'Now Playing: [{track["title"]}]({track["uri"]})'
            await ctx.send(embed = embed)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """ disconnect if left alone in voice channel """
        if member.id != self.bot.user.id and member.guild.voice_client:
            if before.channel == member.guild.voice_client.channel and len(member.guild.voice_client.channel.members) == 1:

                # Start disconnect timer.
                time = 0
                while True:
                    await asyncio.sleep(1)
                    time += 1
                    if not member.guild.voice_client:
                        break
                    if len(member.guild.voice_client.channel.members) != 1:
                        break
                    if time == 90:
                        player = self.bot.lavalink.player_manager.get(member.guild.id)
                        player.queue.clear()
                        await player.stop()
                        await member.guild.voice_client.disconnect(force=True)
                        break


def setup(bot):
    bot.add_cog(Music(bot))