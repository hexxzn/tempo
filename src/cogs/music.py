from discord.ext import commands
from discord import Embed
import lavalink

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.music = lavalink.Client(self.bot.user.id)
        self.bot.music.add_node('localhost', 7000, 'testing', 'na', 'music-node')
        self.bot.add_listener(self.bot.music.voice_update_handler, 'on_socket_response')
        self.bot.music.add_event_hook(self.track_hook)

    @commands.command(name='play')   # play a song or add to queue
    async def play(self, ctx, *, query):
        print("!play")
        try:
            member = ctx.author.name
            channel = ctx.author.voice.channel
            player = self.bot.music.player_manager.create(ctx.guild.id, endpoint=str(ctx.guild.region))   # connect player to node
        except AttributeError:   # if user is not in accessible voice channel ('User' object has no attribute 'voice')
            return await ctx.send('Unable to locate user/voice channel.')
        except Exception as error:   # except doesn't recognize NodeException?
            print(error)
            return await ctx.send('No available nodes.')

        if not player.is_connected:
            player.store('channel', ctx.channel.id)
            await self.connect_to(ctx.guild.id, ctx.author.voice.channel.id)   # connect to voice channel

        player = self.bot.music.player_manager.get(ctx.guild.id)
        query = f'ytsearch:{query}'
        results = await player.node.get_tracks(query)
        tracks = results['tracks'][0:5]
        query_result = '__**0.** None__ \n'
        i = 0

        for track in tracks:
            i = i + 1
            query_result = query_result + f'**{i}.** {track["info"]["title"]}\n'
            # track_list = Embed(color=discord.Color.from_rgb(0, 198, 236))
            track_list = Embed()
            track_list.title = "__Enter Track Number__"
            track_list.description = query_result
        embed_message = await ctx.channel.send(embed=track_list)

        def check(m):
            return m.author.id == ctx.author.id

        response = await self.bot.wait_for('message', check=check)
        if not response.content.isnumeric() or int(response.content) not in range(1, len(tracks) + 1):
            try:
                await embed_message.delete()
                await response.delete()
            except:
                await ctx.send("**Warning**: Bot needs __Manage Messages__ permission to remove track selection messages.")
            return

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

    @commands.command(name='next')   # play after current song (first in queue)
    async def next(self, ctx, *, query):
        print("!next")
        try:
            member = ctx.author.name
            channel = ctx.author.voice.channel
            player = self.bot.music.player_manager.create(ctx.guild.id, endpoint=str(ctx.guild.region))   # connect player to node
        except AttributeError:   # if user is not in accessible voice channel ('User' object has no attribute 'voice')
            return await ctx.send('Unable to locate user/voice channel.')
        except Exception as error:   # except doesn't recognize NodeException?
            print(error)
            return await ctx.send('No available nodes.')

        if not player.is_connected:
            player.store('channel', ctx.channel.id)
            await self.connect_to(ctx.guild.id, ctx.author.voice.channel.id)   # connect to voice channel

        player = self.bot.music.player_manager.get(ctx.guild.id)
        query = f'ytsearch:{query}'
        results = await player.node.get_tracks(query)
        tracks = results['tracks'][0:5]
        query_result = '__**0.** None__ \n'
        i = 0

        for track in tracks:
            i = i + 1
            query_result = query_result + f'**{i}.** {track["info"]["title"]}\n'
            # track_list = Embed(color=discord.Color.from_rgb(0, 198, 236))
            track_list = Embed()
            track_list.title = "__Enter Track Number__"
            track_list.description = query_result
        embed_message = await ctx.channel.send(embed=track_list)

        def check(m):
            return m.author.id == ctx.author.id

        response = await self.bot.wait_for('message', check=check)
        if not response.content.isnumeric() or int(response.content) not in range(1, len(tracks) + 1):
            try:
                await embed_message.delete()
                await response.delete()
            except:
                await ctx.send("**Warning**: Bot needs __Manage Messages__ permission to remove track selection messages.")
            return

        track = tracks[int(response.content)-1]
        player.add(requester=ctx.author.id, track=track, index=0)
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
            await ctx.send('**Next**: ' + track["info"]["title"])

    @commands.command(name='song')   # show current track info
    async def song(self, ctx):
        try:
            player = self.bot.music.player_manager.get(ctx.guild.id)
            if player != None and player.current != None:
                await ctx.send('**Now Playing**: ' + player.current.title)
            else:
                await ctx.send('Bot is not playing music.')
        except Exception as error:
            print(error)

    @commands.command(name='skip')   # skip to next track in queue
    async def skip(self, ctx):
        print("!skip")
        try:
            player = self.bot.music.player_manager.get(ctx.guild.id)
            await player.skip()
            if len(player.queue) >= 0:
                track = player.current.title
                await ctx.send('**Now Playing**: ' + track)
        except Exception as error:
            print(error)

    @commands.command(name='stop')   # stop playback and clear queue
    async def stop(self, ctx):
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

    @commands.command(name='pause')   # pause playback
    async def pause(self, ctx):
        print("!pause")
        try:
            player = self.bot.music.player_manager.get(ctx.guild.id)
            await player.set_pause(True)
            await ctx.send('**Paused**: ' + "Use command **!resume** to unpause")
        except Exception as error:
            print(error)

    @commands.command(name='resume')   # unpause playback
    async def resume(self, ctx):
        print("!resume")
        player = self.bot.music.player_manager.get(ctx.guild.id)
        await player.set_pause(False)
        await ctx.send('**Resumed**: ' + player.current.title)

    @commands.command(name='ff')   # fast forward given number of seconds
    async def ff(self, ctx, seconds):
        print("!ff")
        try:
            player = self.bot.music.player_manager.get(ctx.guild.id)
            await player.seek(player.position + int(seconds) * 1000)
            await ctx.send("**Fast Forward**: " + seconds + " seconds \n" + "Buffering...")
        except Exception as error:
            await ctx.send('Bot is not playing music.')
            print(error)

    @commands.command(name='rw')   # rewind given number of seconds
    async def rw(self, ctx, seconds):
        print("!rw")
        try:
            player = self.bot.music.player_manager.get(ctx.guild.id)
            await player.seek(player.position - int(seconds) * 1000)
            await ctx.send("**Rewind**: " + seconds + " seconds \n" + "Buffering...")
        except Exception as error:
            await ctx.send('Bot is not playing music.')
            print(error)

    @commands.command(name='restart')   # return to beginning of current track
    async def restart(self, ctx):
        print("!restart")
        try:
            player = self.bot.music.player_manager.get(ctx.guild.id)
            await player.seek(player.position - player.position)
            await ctx.send("**Now Playing**: " + player.current.title)
        except Exception as error:
            await ctx.send('Bot is not playing music.')
            print(error)

    @commands.command(name='qq')   # show length of queue
    async def qq(self, ctx):
        print("!qq")
        player = self.bot.music.player_manager.get(ctx.guild.id)
        if player == None:
            await ctx.send("**Queue**: 0")
        else:
            await ctx.send("**Queue**: " + str(len(player.queue)))

    @commands.command(name='help')   # show command list in text channel
    async def help(self, ctx):
        print("!help")
        help_menu = Embed()
        help_menu.title = "__Tempo Commands__"
        help_menu.description = ("**!play <song name, artist>** \n" +
                                "— play a song or add to queue \n" +
                                "**!next <song name, artist>** \n" +
                                "— play after current song (first in queue) \n" +
                                "**!song** \n" +
                                "— show current track info \n" +
                                "**!skip** \n" +
                                "— skip to next track in queue \n" +
                                "**!stop** \n" +
                                "— stop playback and clear queue \n" +
                                "**!pause** \n" +
                                "— pause playback \n" +
                                "**!resume** \n" +
                                "— unpause playback \n" +
                                "**!ff <seconds>** \n" +
                                "— fast forward given number of seconds \n" +
                                "**!rw <seconds>** \n" +
                                "— rewind given number of seconds \n" +
                                "**!restart** \n" +
                                "— return to beginning of current track \n" +
                                "**!qq** \n" +
                                "— show length of queue \n" +
                                "\n __**Developed by Hexxzn**__")
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
    
    # @commands.command(name='clean')
    # async def clean(self, ctx):
    #     try:
    #         print("!clean")
    #         await ctx.channel.purge()
    #     except Exception as error:
    #         print(error)

    # @commands.command(name='test')
    # async def tempot(self, ctx):
    #     player = self.bot.music.player_manager.get(ctx.guild.id)
    #     print(player.queue)

    # @commands.command(name='tempo')
    # async def tempo(self, ctx):
    #     """!tempo || bot developed by hexxzn"""
    #     await ctx.send(':wave:')

def setup(bot):
    bot.add_cog(Music(bot))