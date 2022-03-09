from discord.ext import commands
from tokens import *
import discord

# intents = discord.Intents.default()
# intents.members = True
bot = commands.Bot(command_prefix = '!', case_insensitive = True, help_command = None)

@bot.event
async def on_ready():
    bot.load_extension('cogs.music')
    bot.load_extension('cogs.chat')
    await bot.change_presence(activity=discord.Game(name="!help"))
    print(f'{bot.user} is online.')
    print('--------------------')

bot.run(beta_token)