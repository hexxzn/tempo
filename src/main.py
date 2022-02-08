from discord.ext import commands
from apikeys import *
import discord

bot = commands.Bot(command_prefix = '!', help_command = None)

@bot.event
async def on_ready():
    bot.load_extension('cogs.music')
    await bot.change_presence(activity=discord.Game(name="!help"))
    print(f'{bot.user} is online.')
    print('--------------------')

bot.run(beta_token)