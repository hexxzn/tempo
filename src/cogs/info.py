import nextcord as nxt
from nextcord.ext import commands as cmd
from lyricsgenius import Genius
from tokens import *

class Info(cmd.Cog):
    def __init__(self, bot):
        self.bot = bot


    # Get song lyrics
    @cmd.command(aliases=['l'])
    async def lyrics(self, ctx, *, query: str = ''):
        # Create embed and set border color
        embed = nxt.Embed(color=nxt.Color.from_rgb(134, 194, 50))

        # If user input invalid
        if query == '':
            # Send embed message
            embed.description = 'What song? Try `lyrics <song title and artist>` to search for lyrics.'
            return await ctx.send(embed = embed)
        
        # Lyrics Genius
        genius = Genius(genius_token)

        try:
            # Get song info from Genius
            song = genius.search_song(query, '')
        except Exception as e:
            embed.description = 'Failed to connect to Genius. Please try again.'
            await ctx.send(embed = embed)
            print(e)
            return

        # If song info not found
        if not song:
            # Send embed message
            embed.description = f'No lyrics found for: {query} \n'
            return await ctx.send(embed = embed)
        
        # Add song title to embed title
        embed_title = f'__**{song.artist} - {song.title}**__ \n \n'

        # Remove Pyong and "Embed" text from end of lyrics string
        for char in song.lyrics[-10:]:
            if char.isnumeric():
                end_index = song.lyrics[-10:].index(char)
                song.lyrics = song.lyrics[:-(10 - end_index)]
                break

        # If length of song title + song lyrics is less than 4096 characters
        if len(embed_title) + len(song.lyrics) < 4096:
            embed.description = embed_title + song.lyrics
            await ctx.send(embed = embed)

        # If length of song title + song lyrics exceeds 4096 characters
        else:
            embed.description = embed_title
            lyrics_chunk = song.lyrics[:4096 - len(embed.description)]

            break_index = 0
            for char in lyrics_chunk[::-1]:
                break_index += 1
                if char == '\n':
                    break

            lyrics_chunk = lyrics_chunk[:-break_index]
            embed.description += lyrics_chunk
            await ctx.send(embed = embed)

            song.lyrics = song.lyrics[len(lyrics_chunk):]

            while len(song.lyrics) > 0:
                embed.description = ''

                if len(song.lyrics) > 4096:
                    lyrics_chunk = song.lyrics[:4096]
                    break_index = 0
                
                    for char in lyrics_chunk[::-1]:
                        break_index += 1
                        if char == '\n':
                            break
                    
                    lyrics_chunk = lyrics_chunk[:-break_index]
                
                else:
                    lyrics_chunk = song.lyrics

                embed.description += lyrics_chunk

                await ctx.send(embed = embed)
                song.lyrics = song.lyrics[len(lyrics_chunk):]

    # Display a list of servers Tempo is a member of (developer only)
    @cmd.command(aliases=['gl'])
    async def guild_list(self, ctx):
        # Command can only be used by developer
        if ctx.author.id != developer:
            return

        # Iterate through each guild Tempo is a member of
        guild_list = []
        playing = 0
        for guild in self.bot.guilds:
            tempo = guild.get_member(self.bot.user.id)

            # If Tempo is not connected to a voice channel
            if tempo.voice == None:
                status_icon = "🔴"
            else:
                status_icon = "🟢"
                playing += 1

            # Add relevant info to guild list
            guild_info = {
                "status": status_icon,
                "guild_name": guild,
                "guild_owner": await self.bot.fetch_user(guild.owner_id),
                "join_date": tempo.joined_at,
                "join_date_string": tempo.joined_at.strftime("%m-%d-%y"),
            }
            guild_list.append(guild_info)

        # Create info string with guilds sorted by bot join date
        info_list = ''
        for guild_info in sorted(guild_list, key = lambda date: date["join_date"]):
            info_list += f'`{guild_info["status"]}` `[{guild_info["join_date_string"]}]` `{guild_info["guild_name"]}` `({guild_info["guild_owner"]})`\n'

        # Create embed and set border color
        embed = nxt.Embed(color=nxt.Color.from_rgb(134, 194, 50))
        embed.add_field(name=f'__Guilds Joined__', value=f'`{len(self.bot.guilds)}`', inline=True)
        embed.add_field(name=f'__Active Players__', value=f'`{playing}`', inline=True)
        embed.add_field(name=f'__Guild Details__', value=info_list, inline=False)

        # Send embed message
        await ctx.send(embed = embed)

    # Display a clickable link to invite Tempo
    @cmd.command(aliases=['inv'])
    async def invite(self, ctx):
        # Create and send embed
        embed = nxt.Embed(color=nxt.Color.from_rgb(134, 194, 50))
        embed.description = f'[Invite Tempo](https://discord.com/api/oauth2/authorize?client_id=897864886095343687&permissions=3156992&scope=bot%20applications.commands)'
        await ctx.send(embed = embed)

# Add cog
def setup(bot):
    bot.add_cog(Info(bot))