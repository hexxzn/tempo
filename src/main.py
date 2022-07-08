import nextcord as nxt
from nextcord.ext import commands as cmd
from tokens import *
import sqlite3
from sqlite3 import Error

intents = nxt.Intents.default()
intents.message_content = True

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

# Get server specific command prefix from database
async def get_prefix(bot, ctx):
    # Connect to database
    connection = None
    try:
        connection = sqlite3.connect('./tempo.sqlite')
    except Error as e:
        print(f'SQLite Error: {e}')

    # Execute query
    cursor = connection.cursor()
    try:
        data = None
        cursor.execute(f'SELECT Prefix FROM Guilds Where GuildID = {ctx.guild.id}')
        data = cursor.fetchone()
    except Error as e:
        print(f'SQLite Error: {e}')

    # Close connection
    connection.close()

    # If prefix for guild exists in database return it, otherwise return the default prefix
    if data:
        return data[0]
    else:
        return '!'

bot = cmd.Bot(command_prefix = get_prefix, case_insensitive = True, help_command = None, intents = intents)

@bot.event
async def on_ready():
    bot.load_extension('cogs.music')
    bot.load_extension('cogs.help')
    bot.load_extension('cogs.info')
    bot.load_extension('cogs.data')

    # Set custom Discord status
    await bot.change_presence(activity=nxt.Activity(type=nxt.ActivityType.listening, name="!help"))

    print(f'{bot.user} is online.')
    print('--------------------')

@bot.event
async def on_guild_join(ctx):
    # Connect to database
    connection = await create_connection('././tempo.sqlite')

    # Get data
    owner = await bot.fetch_user(ctx.owner_id)
    guild_id = ctx.id
    guild_name = ctx
    admin_id = owner.id
    admin_name = f'{owner.name}#{str(owner.discriminator)}'
    members = ctx.member_count
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

@bot.event
async def on_guild_remove(ctx):
    # Connect to database
    connection = await create_connection('././tempo.sqlite')

    # SQLite query
    insert_row = f"""
        DELETE FROM Guilds
        WHERE GuildID = {ctx.id}
    """
    # Remove data
    await execute_query(connection, insert_row)

    # Close connection to database
    connection.close()

# Start Tempo
bot.run(beta_token)