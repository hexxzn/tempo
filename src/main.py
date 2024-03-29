import asyncio
import nextcord as nxt
from nextcord.ext import commands as cmd
from tokens import *

intents = nxt.Intents.default()
intents.message_content = True

bot = cmd.Bot(command_prefix = '!', case_insensitive = True, help_command = None, intents = intents)

@bot.event
async def on_ready():
    bot.load_extension('cogs.music')
    bot.load_extension('cogs.help')
    bot.load_extension('cogs.info')

    print(f'{bot.user} is online.')
    print('--------------------')

    while True:
        # Set custom Discord status
        await bot.change_presence(activity=nxt.Activity(type=nxt.ActivityType.listening, name="!help"))

        # Refresh custom Discord status
        await asyncio.sleep(3600)

# Start Tempo
bot.run(beta_token)