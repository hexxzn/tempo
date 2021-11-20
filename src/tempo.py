import discord
from discord.ext import commands

bot = commands.Bot(command_prefix = '!')

class MainCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

@bot.event
async def on_ready():
    print(f'{bot.user} has logged in.')
    bot.load_extension('cogs.music')
    await bot.change_presence(activity=discord.Game(name="!help"))

bot.run("ODk3ODY0ODg2MDk1MzQzNjg3.YWb31g.7AdVm_bYXeLKCfqI8PXtt9GgPxs")