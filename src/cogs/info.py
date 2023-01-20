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
                
        # Get song info from Genius
        song = genius.search_song(query, '')

        # If song info not found
        if not song:
            # Send embed message
            embed.description = f'No lyrics found for: {query} \n'
            return await ctx.send(embed = embed)

        # Add song title to embed title
        embed_title = f'__**{song.artist} - {song.title}**__ \n \n'

        # Remove song title from embed description content (since it's already displayed in embed title)
        song.lyrics = song.lyrics[len(song.title)+7:-5]

        # Remove ID number from end of lyrics string
        for char in song.lyrics[len(song.lyrics)-7:]:
            if char.isnumeric():
                song.lyrics = song.lyrics[:-1]

        # Message to display if lyrics string exceeds max embed message length
        char_limit_message = '... \n \n [Exceeds maximum size of 4096 characters.]'

        # If lyrics string does not exceed max embed message length
        if len(embed_title) + len(song.lyrics) < 4096:
            embed.description = embed_title + song.lyrics
        else:
            embed.description = embed_title + song.lyrics[:4096 - (len(embed_title) + len(char_limit_message))] + char_limit_message
            print(len(embed.description))

        # Send embed message
        await ctx.send(embed = embed)

    @cmd.command(aliases=['inv'])
    async def invite(self, ctx):
        # Create embed and set border color
        embed = nxt.Embed(color=nxt.Color.from_rgb(134, 194, 50))

        # Set embed message
        embed.description = (
            '[Invite Tempo](https://discord.com/api/oauth2/authorize?client_id=897864886095343687&permissions=3156992&scope=bot%20applications.commands)'
        )

        await ctx.send(embed = embed)

    @cmd.command(aliases=['gl'])
    async def guild_list(self, ctx):
        # Create embed and set border color
        embed = nxt.Embed(color=nxt.Color.from_rgb(134, 194, 50))
        embed.description = '**Guild List** \n'

        # Iterate through each guild Tempo is a member of
        guild_list = []
        for guild in self.bot.guilds:
            tempo = guild.get_member(self.bot.user.id)
            guild_info = {
                "guild_name": guild,
                "guild_owner": await self.bot.fetch_user(guild.owner_id),
                "join_date": tempo.joined_at,
                "join_date_string": tempo.joined_at.strftime("%m-%d-%y"),
            }
            guild_list.append(guild_info)

        # Build embed message with guilds sorted by bot join date
        for guild_info in sorted(guild_list, key = lambda date: date["join_date"]):
            embed.description += f'`[{guild_info["join_date_string"]}] {guild_info["guild_name"]} ({guild_info["guild_owner"]})` \n'

        # Send embed message
        await ctx.send(embed = embed)

# Add cog
def setup(bot):
    bot.add_cog(Info(bot))