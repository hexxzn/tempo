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

# Sets default prefix for direct messages
prefix = '!'

# Get server specific command prefix from database
@cmd.guild_only()
async def get_prefix(bot, ctx):
    if isinstance(ctx.channel, nxt.channel.DMChannel):
        return '!'

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

bot = cmd.Bot(command_prefix = prefix, case_insensitive = True, help_command = None, intents = intents)

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

    # Create embed and set border color
    embed = nxt.Embed(color=nxt.Color.from_rgb(134, 194, 50))
    embed.description = (
            '**Hey! Here\'s some info on how to get started.** \n\n'
            '__**Help**__ \n'
            'Use the `!help` command to get a list of all the commands Tempo has to offer. Want to know how a specific command works? Use `!help` followed by the name of the command you want more information on. For example `!help search` will give you helpful information on the `!search` command. \n\n'

            '__**Music**__ \n'
            'To play music in your current voice channel, use the `!play` command followed by the name of a song. For example `!play cosmica sublab` will play the song Cosmica by Sublab & Azaleh. \n\n'

            '__**Permissions**__ \n'
            'Use the `!role` command to select which members have permission to use Tempo. Tempo is available to @everyone by default. \n\n'

            '__**Prefix**__ \n'
            'Use the `!prefix` command to change Tempo\'s command prefix. For example `!prefix ?` will change the command prefix from ! to ?. \n\n'

            '**Thanks for the invite. Enjoy!**'
        )

    # Send private message to server owner
    channel = await owner.create_dm()
    await channel.send(embed=embed)

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