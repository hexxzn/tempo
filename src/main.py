from nextcord.ext import commands as cmd
import nextcord as nxt
from tokens import *
import asyncio

intents = nxt.Intents.default()
intents.message_content = True

bot = cmd.Bot(command_prefix = '!', case_insensitive = True, help_command = None, intents = intents)

@bot.event
async def on_ready():
    await bot.wait_until_ready()

    try:
        bot.load_extension('cogs.music')
        bot.load_extension('cogs.help')
        bot.load_extension('cogs.info')
        print("\nCogs loaded successfully...")

        # Explicitly register commands
        if bot.application_id:
            await bot.sync_all_application_commands()
            print("Slash commands synced successfully...")

    except Exception as e:
        print(f"Error during bot startup: {e}")

    print(f'Tempo is online.\n')

    while True:
        # Set custom Discord status
        await bot.change_presence(activity=nxt.Activity(type=nxt.ActivityType.listening, name="!help"))

        # Refresh custom Discord status
        await asyncio.sleep(3600)

# Start Tempo
bot.run(beta_token)