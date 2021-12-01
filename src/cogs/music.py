from discord.ext.commands import bot
import lavalink
import discord
from discord import Embed
from discord.ext import commands

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.music = lavalink.Client(self.bot.user.id)
        self.bot.music.add_node('localhost', 7000, 'testing', 'na', 'music-node')
        self.bot.add_listener(self.bot.music.voice_update_handler, 'on_socket_response')
        self.bot.music.add_event_hook(self.track_hook)

    @commands.command(name='play')
    async def play(self, ctx, *, query):
        """- Plays or queues a song"""
        member = ctx.author.name
        try:
            vc = ctx.author.voice.channel
        except:
            vc = None
            await ctx.send("**Error**: Unable to locate user voice channel.")
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
    
    # @commands.command(name='clean')
    # async def clean(self, ctx):
    #     """- Deletes messages in text channel"""
    #     await ctx.channel.purge()

    @commands.command(name='skip')
    async def skip(self, ctx):
        """- Skips current song"""
        try:
            player = self.bot.music.player_manager.get(ctx.guild.id)
            await player.skip()
            track = player.current.title
            await ctx.send('**Now Playing**: ' + track)
        except Exception as error:
            print(error)

    @commands.command(name='pause')
    async def pause(self, ctx):
        """- Pauses music"""
        try:
            player = self.bot.music.player_manager.get(ctx.guild.id)
            await player.set_pause(True)
            await ctx.send('**Paused**')
        except Exception as error:
            print(error)

    @commands.command(name='resume')
    async def resume(self, ctx):
        """- Resumes music"""
        player = self.bot.music.player_manager.get(ctx.guild.id)
        await player.set_pause(False)
        await ctx.send('**Resumed**')

    @commands.command(name='stop')
    async def stop(self, ctx):
        """- Stops music"""
        player = self.bot.music.player_manager.get(ctx.guild.id)
        await player.stop()
        await ctx.send('**Stopped**')

    @commands.command(name='tempo')
    async def tempo(self, ctx):
        """- Developed by Hexxzn"""
        await ctx.send(':wave:')

    async def track_hook(self, event):
        if isinstance(event, lavalink.events.QueueEndEvent):
            guild_id = int(event.player.guild_id)
            await self.connect_to(guild_id, None)

    async def connect_to(self, guild_id: int, channel_id: str):
        ws = self.bot._connection._get_websocket(guild_id)
        await ws.voice_state(str(guild_id), channel_id)

def setup(bot):
    bot.add_cog(Music(bot))