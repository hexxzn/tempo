import nextcord as nxt
from nextcord.ext import commands as cmd
from tokens import *

intents = nxt.Intents.default()
intents.message_content = True

bot = cmd.Bot(command_prefix = prefix, case_insensitive = True, help_command = None, intents = intents)

@bot.event
async def on_ready():
    bot.load_extension('cogs.music')
    bot.load_extension('cogs.help')
    bot.load_extension('cogs.info')
    await bot.change_presence(activity=nxt.Activity(type=nxt.ActivityType.listening, name="!help"))
    print(f'{bot.user} is online.')
    print('--------------------')

bot.run(beta_token)

