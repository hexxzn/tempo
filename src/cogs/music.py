from discord.ext import commands
from discord import Embed
import lavalink
import asyncio

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.music = lavalink.Client(self.bot.user.id)
        self.bot.music.add_node('localhost', 7000, 'testing', 'na', 'music-node')
        self.bot.add_listener(self.bot.music.voice_update_handler, 'on_socket_response')
        self.bot.music.add_event_hook(self.track_hook)

    @commands.command(name='play')
    async def play(self, ctx, *, query):
        """!play <song name, artist> || play a song or add to queue"""
        print("!play")
        member = ctx.author.name
        try:
            vc = ctx.author.voice.channel
        except:
            vc = None
            await ctx.send("Unable to locate user voice channel.")
        if member is not None and vc is not None:
            player = self.bot.music.player_manager.create(ctx.guild.id, endpoint=str(ctx.guild.region))
            if not player.is_connected:
                player.store('channel', ctx.channel.id)
                await self.connect_to(ctx.guild.id, ctx.author.voice.channel.id)

        try:
            player = self.bot.music.player_manager.get(ctx.guild.id)
            query = f'ytsearch:{query}'
            results = await player.node.get_tracks(query)
            tracks = results['tracks'][0:5]
            query_result = ''
            i = 0

            for track in tracks:
                i = i + 1
                query_result = query_result + f'**{i}.** {track["info"]["title"]}\n'
                # track_list = Embed(color=discord.Color.from_rgb(0, 198, 236))
                track_list = Embed()
                track_list.title = "__Enter Desired Track Number__"
                track_list.description = query_result
            embed_message = await ctx.channel.send(embed=track_list)

            def check(m):
                return m.author.id == ctx.author.id

            response = await self.bot.wait_for('message', check=check)
            track = tracks[int(response.content)-1]
            player.add(requester=ctx.author.id, track=track)
            if not player.is_playing:
                try:
                    await embed_message.delete()
                    await response.delete()
                except:
                    await ctx.send("**Warning**: Bot needs __Manage Messages__ permission to remove track selection messages.")
                await ctx.send('**Now Playing**: ' + track["info"]["title"])
                await player.play()
                await player.set_volume(15)
            else:
                try:
                    await embed_message.delete()
                    await response.delete()
                except:
                    await ctx.send("**Warning**: Bot needs __Manage Messages__ permission to remove track selection messages.")
                await ctx.send('**Queued**: ' + track["info"]["title"])
        except Exception as error:
            print(error)
    
    @commands.command(name='clean')
    async def clean(self, ctx):
        """!clean || delete messages in text channel"""
        print("!clean")
        await ctx.channel.purge()

    @commands.command(name='skip')
    async def skip(self, ctx):
        """!skip || skip to next song in queue"""
        print("!skip")
        try:
            player = self.bot.music.player_manager.get(ctx.guild.id)
            await player.skip()
            if len(player.queue) > 0:
                track = player.current.title
                await ctx.send('**Now Playing**: ' + track)
        except Exception as error:
            print(error)

    @commands.command(name='pause')
    async def pause(self, ctx):
        """!pause || pause playback"""
        print("!pause")
        try:
            player = self.bot.music.player_manager.get(ctx.guild.id)
            await player.set_pause(True)
            await ctx.send('**Paused**: ' + "Use command **!resume** to unpause")
        except Exception as error:
            print(error)

    @commands.command(name='resume')
    async def resume(self, ctx):
        """!resume || resume playback"""
        print("!resume")
        player = self.bot.music.player_manager.get(ctx.guild.id)
        await player.set_pause(False)
        await ctx.send('**Resumed**: ' + player.current.title)

    @commands.command(name='stop')
    async def stop(self, ctx):
        """!stop || stop playback and clear queue"""
        print("!stop")
        try:
            player = self.bot.music.player_manager.get(ctx.guild.id)
            await player.queue.clear()
        except Exception as error:
            print(error)
        try:
            player = self.bot.music.player_manager.get(ctx.guild.id)
            guild_id = int(player.guild_id)
            await player.stop()
            
            await self.connect_to(guild_id, None)
            await ctx.send('**Stopped**: Queue cleared')
        except Exception as error:
            await ctx.send('Bot is not playing music.')
            print(error)

    @commands.command(name='rw')
    async def rw(self, ctx, seconds):
        """!rw <seconds> || rewind given number of seconds"""
        print("!rw")
        try:
            player = self.bot.music.player_manager.get(ctx.guild.id)
            await player.seek(player.position - int(seconds) * 1000)
            await ctx.send("**Rewind**: " + seconds + " seconds \n" + "Buffering...")
        except Exception as error:
            await ctx.send('Bot is not playing music.')
            print(error)

    @commands.command(name='ff')
    async def ff(self, ctx, seconds):
        """!ff <seconds> || fast forward given number of seconds"""
        print("!ff")
        try:
            player = self.bot.music.player_manager.get(ctx.guild.id)
            await player.seek(player.position + int(seconds) * 1000)
            await ctx.send("**Fast Forward**: " + seconds + " seconds \n" + "Buffering...")
        except Exception as error:
            await ctx.send('Bot is not playing music.')
            print(error)

    @commands.command(name='restart')
    async def restart(self, ctx):
        """!restart || return to beginning of current track"""
        print("!restart")
        try:
            player = self.bot.music.player_manager.get(ctx.guild.id)
            await player.seek(player.position - player.position)
            await ctx.send("**Now Playing**: " + player.current.title)
        except Exception as error:
            await ctx.send('Bot is not playing music.')
            print(error)

    @commands.command(name='qq')
    async def qq(self, ctx):
        """!qq || check length of queue"""
        print("!qq")
        player = self.bot.music.player_manager.get(ctx.guild.id)
        if player == None:
            await ctx.send("**Queue**: 0")
        else:
            await ctx.send("**Queue**: " + str(len(player.queue)))

    @commands.command(name='help')
    async def help(self, ctx):
        print("!help")
        help_menu = Embed()
        help_menu.title = "__Tempo Commands__"
        help_menu.description = ("**!play <song name, artist>** \n" +
                                "— play a song or add to queue \n" +
                                "**!stop** \n" +
                                "— stop playback and clear queue \n" +
                                "**!skip** \n" +
                                "— skip to next song in queue \n" +
                                "**!pause** \n" +
                                "— pause playback \n" +
                                "**!resume** \n" +
                                "— unpause playback \n" +
                                "**!restart** \n" +
                                "— return to beginning of current track \n" +
                                "**!ff <seconds>** \n" +
                                "— fast forward given number of seconds \n" +
                                "**!rw <seconds>** \n" +
                                "— rewind given number of seconds \n" +
                                "**!qq** \n" +
                                "— check length of queue \n" +
                                "**!clean** \n" +
                                "— delete messages in text channel \n\n" +
                                "__**Developed by Hexxzn**__")
        await ctx.channel.send(embed=help_menu)

    async def track_hook(self, event):
        if isinstance(event, lavalink.events.QueueEndEvent):
            # guild_id = int(event.player.guild_id)
            # player = self.bot.music.player_manager.get(guild_id)
            # print("queue empty. disconnect in 180 seconds.")
            # await asyncio.sleep(180)
            # if not player.is_playing:
            #     print("queue empty for 180 seconds. disconnecting.")
            #     await player.stop()
            #     await self.connect_to(guild_id, None)
            guild_id = int(event.player.guild_id)
            await self.connect_to(guild_id, None)

    async def connect_to(self, guild_id: int, channel_id: str):
        ws = self.bot._connection._get_websocket(guild_id)
        await ws.voice_state(str(guild_id), channel_id)
    
    # @commands.command(name='tempo')
    # async def tempo(self, ctx):
    #     """!tempo || bot developed by hexxzn"""
    #     await ctx.send(':wave:')

    # @commands.command(name='test')
    # async def tempot(self, ctx):
    #     player = self.bot.music.player_manager.get(ctx.guild.id)
    #     await player.queue.clear()

def setup(bot):
    bot.add_cog(Music(bot))