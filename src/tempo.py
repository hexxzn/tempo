from discord.ext import commands
from dotenv import load_dotenv
import discord
import os

bot = commands.Bot(command_prefix = '!')

class MainCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

@bot.event
async def on_ready():
    print(f'{bot.user} has logged in.')
    bot.load_extension('cogs.music')
    await bot.change_presence(activity=discord.Game(name="!help"))

@bot.event
async def on_voice_state_update(member, before, after):
    if member == bot.user:
        player = bot.music.player_manager.get(member.guild.id)
        if player != None and before.channel != None and after.channel != None:   # pause player if bot changes channel
            await player.set_pause(True)
        elif player != None and before.channel != None and after.channel == None:   # stop player if bot disconnects
            await player.stop()

load_dotenv()
token = os.getenv('TOKEN')

bot.run(token)