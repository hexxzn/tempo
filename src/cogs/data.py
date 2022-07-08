import nextcord as nxt
import sqlite3
from tokens import *
from sqlite3 import Error
from nextcord.ext import commands as cmd
import string

# Connect to database
async def create_connection(path):
    connection = None
    try:
        connection = sqlite3.connect(path)
    except Error as e:
        print(f'SQLite Error: {e}')

    return connection

# Execute database query
async def execute_query(connection, query):
    cursor = connection.cursor()
    try:
        cursor.execute(query)
        connection.commit()
    except Error as e:
        print(f'SQLite Error: {e}')

class Data(cmd.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Update SQLite database
    @cmd.command(aliases = ['udb'])
    async def update_database(self, ctx):
        if not ctx.author.id == developer:
            return

        # Connect to database
        connection = await create_connection('././tempo.sqlite')

        # SQLite query
        create_users_table = """
        CREATE TABLE IF NOT EXISTS Guilds (
            GuildID INTEGER PRIMARY KEY,
            GuildName TEXT NOT NULL,
            AdminID INTEGER NOT NULL,
            AdminName TEXT NOT NULL,
            Members INTEGER NOT NULL,
            Prefix TEXT NOT NULL
        );
        """

        # Create table if table doesn't already exist
        await execute_query(connection, create_users_table)

        # Update data for each guild
        for guild in self.bot.guilds:
            # Get data
            owner = await self.bot.fetch_user(guild.owner_id)
            guild_id = guild.id
            guild_name = guild
            admin_id = owner.id
            admin_name = f'{owner.name}#{str(owner.discriminator)}'
            members = guild.member_count
            prefix = '!'

            # SQLite query
            insert_row = f"""
                INSERT OR REPLACE INTO Guilds (GuildID, GuildName, AdminID, AdminName, Members, Prefix)
                VALUES({guild_id}, '{guild_name}', {admin_id}, '{admin_name}', {members}, '{prefix}');
            """
            # Insert data
            await execute_query(connection, insert_row)

        # Close connection to database
        connection.close()

    # Change bot prefix for guild
    @cmd.command(aliases = ['pf'])
    async def prefix(self, ctx, prefix = '!'):
        # Create embed and set border color
        embed = nxt.Embed(color=nxt.Color.from_rgb(134, 194, 50))

        # If prefix exceeds two characters
        if len(prefix) > 2:
            embed.description = 'Prefix must be two characters or less.'
            return await ctx.send(embed=embed)

        # If prefix is not a standard keyboard character
        check_string = string.ascii_letters + string.digits + string.punctuation
        for char in prefix:
            if char not in check_string:
                embed.description = 'Prefix must consist of letters, numbers or punctuation characters.'
                return await ctx.send(embed=embed)

        # Get admin ID
        owner = await self.bot.fetch_user(ctx.guild.owner_id)

        # Check if user has privelege to use command (admin only)
        if ctx.author.id != owner.id:
            # Send embed message
            embed.description = 'Only the server admin has access to the `volume` command.'
            return await ctx.send(embed = embed)

        # Connect to database
        connection = await create_connection('././tempo.sqlite')

        # Update prefix value for server
        change_prefix = f"""
            UPDATE Guilds
            SET Prefix = '{prefix}'
            WHERE GuildID = {ctx.guild.id}
        """
        await execute_query(connection, change_prefix)

        # Close connections to database
        connection.close()

        # Send embed message
        embed.description = f'Prefix has been changed to: {prefix}'
        await ctx.send(embed=embed)

# Add cog
def setup(bot):
    bot.add_cog(Data(bot))