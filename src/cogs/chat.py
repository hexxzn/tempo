from discord.ext import commands
from lyricsgenius import Genius
from tokens import *
import discord

genius = Genius(genius_token)


class Chat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def cog_command_error(self, ctx, error):
            if isinstance(error, commands.CommandInvokeError):
                if ctx.guild == None:
                    await ctx.send('Unable to locate user/voice channel.')
                else:
                    await ctx.send(error.original)
                # Log cog errors

    @commands.command(aliases=['bc'])
    async def broadcast(self, ctx, *, message):
        """ send message to all guilds """
        if ctx.author.id == 488812651514691586:
            embed = discord.Embed(color=discord.Color.from_rgb(134, 194, 50))
            embed.description = message
            for guild in self.bot.guilds:
                for channel in guild.text_channels:
                    try:
                        await channel.send(embed = embed)
                    except:
                        continue
                    else:
                        break
        else:
            await ctx.send('You are not authorized to use this command.')

    @commands.command()
    async def stats(self, ctx, *, stat=''):
        if ctx.author.id == 488812651514691586:
            embed = discord.Embed(color=discord.Color.from_rgb(134, 194, 50))
            if stat == '':
                embed.description = '__**!stats <stat>**__ \n' + '**guilds**' + ' — server count \n' + '**guild list**' + ' — list servers \n' + '**players**' + ' — active player count \n'
                return await ctx.send(embed = embed)
            elif stat.lower() == 'guilds':
                # display guild count
                embed.description = f'Tempo is currently a member of {len(self.bot.guilds)} servers.'
                return await ctx.send(embed = embed)
            elif stat.lower() == 'guild list':
                embed.description = ''
                for guild in self.bot.guilds:
                    owner = await self.bot.fetch_user(guild.owner_id)
                    embed.description += f'{guild} ({owner.name}#{owner.discriminator}) \n'
                return await ctx.send(embed = embed)
            elif stat.lower() == 'players':
                # display active player count
                players = 0
                for guild in self.bot.guilds:
                    if guild.voice_client:
                        players += 1
                embed.description = f'Tempo is currently playing music in {players} servers.'
                return await ctx.send(embed = embed)
            else:
                embed.description = f'"{stat}" is not an available stat.'
                return await ctx.send(embed = embed)
        else:
            await ctx.send('You are not authorized to use this command.')

    @commands.command()
    async def purge(self, ctx):
        """ mass delete messages in command channel """
        if ctx.author.id == 488812651514691586:
            await ctx.channel.purge(limit=100)
        else:
            await ctx.send('You are not authorized to use this command.')

    @commands.command(aliases=['h'])
    async def help(self, ctx):
        """ show command list in text channel """
        help_menu = discord.Embed(color=discord.Color.from_rgb(134, 194, 50))
        help_menu.description = (
            '__**Links**__ \n'
            '**[More Info](https://sourceflow.io/tempo)** - More links, commands, updates and unreleased features. \n'
            '**[Invite Tempo](https://discord.com/api/oauth2/authorize?client_id=897864886095343687&permissions=3156992&scope=bot%20applications.commands)** - Invite Tempo to your Discord server. \n'
            '\n'
            '__**Updates**__ \n'
            '**2.7.0** - Added lyrics command. \n'
            '**2.6.0** - Tempo can now stream audio from Twitch and SoundCloud. \n'
            '**2.5.0** - Tempo can now play YouTube livestreams. \n'
            '\n'
            '__**Commands**__ \n'
            '**[!p] [!play] <song title, artist> or <link>** \n' +
            '— play song or add to queue \n'
            '**[!sn] [!song]** \n'
            '— show current track in text channel \n'
            '**[!sk] [!skip]** \n'
            '— skip to next track in queue \n'
            '**[!st] [!stop]** \n'
            '— stop playback and clear queue \n'
            '**[!ps] [!pause]** \n'
            '— pause playback \n'
            '**[!rs] [!resume]** \n'
            '— unpause playback \n'
            '**[!fw] [!forward] <seconds>** \n'
            '— skip forward given number of seconds \n'
            '**[!bw] [!backward] <seconds>** \n'
            '— skip backward given number of seconds \n'
            '**[!re] [!restart]** \n'
            '— return to beginning of current track \n'
            '**[!q] [!queue]** \n'
            '— show active queue in text channel \n'
            '**[!l] [!lyrics] <song title, artist>** \n'
            '— show song lyrics in text channel \n'
            '\n'
            '__**Tempo v2.7.2**__ \n'
            '__**Developed by Hexxzn (Hexxzn#0001)**__'
        )
        await ctx.channel.send(embed=help_menu)

    @commands.command(aliases=['l'])
    async def lyrics(self, ctx, *, query: str = ''):
        if query != '':
            embed = discord.Embed(color=discord.Color.from_rgb(134, 194, 50))
            song = genius.search_song(query, '')

            if song == None:
                embed.description = 'No lyrics found.'
                return await ctx.send(embed = embed)

            song.lyrics = song.lyrics[len(song.title)+7:-5]
            for char in song.lyrics[len(song.lyrics)-7:]:
                if char.isnumeric():
                    song.lyrics = song.lyrics[:-1]
            embed_title = f'__**{song.artist} - {song.title}**__ \n \n'
            char_limit_message = '... \n \n [Exceeds maximum size of 4096 characters.]'

            if len(embed_title) + len(song.lyrics) < 4096:
                embed.description = embed_title + song.lyrics
            else:
                embed.description = embed_title + song.lyrics[:4096 - (len(embed_title) + len(char_limit_message))] + char_limit_message
                print(len(embed.description))

            await ctx.send(embed = embed)

def setup(bot):
    bot.add_cog(Chat(bot))