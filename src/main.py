from nextcord.ext import commands as cmd
import nextcord as nxt
from tokens import *
import asyncio
import random


intents = nxt.Intents.default()
intents.message_content = True
intents.members = True

bot = cmd.Bot(command_prefix = '!', case_insensitive = True, help_command = None, intents = intents)

@bot.event
async def on_ready():
    await bot.wait_until_ready()

    try:
        bot.load_extension('cogs.music')
        bot.load_extension('cogs.help')
        bot.load_extension('cogs.general')
        bot.load_extension('cogs.warning')
        print("\nCogs loaded successfully...")

        # Explicitly register commands
        if bot.application_id:
            await bot.sync_all_application_commands()
            print("Slash commands synced successfully...")

    except Exception as e:
        print(f"Error during bot startup: {e}")

    print(f'Tempo is online.\n')

    statuses = ["Song request? Fire away!", 
                "Max volume. Ready?", 
                "I'm your DJ. What's up?", 
                "Tune in, vibe out.", 
                "Music on, world off.",
                "It's a vibe, trust me.",
                "Yo, pass me the aux.",
                "Vibe check. You're good.",
                "Keep calm, music's here.",
                "Bruh…",
                "When in doubt, vibe out.",
                "You up…?"]
    
    # # Testing: Messsages longer than 25 characters won't fit in status 
    # for status in statuses:
    #     if len(status) > 25:
    #         print('"' + status + '"', "Exceeds 25 character max length.")

    # Periodically update bot status
    while True:
        # Select random status
        status = random.choice(statuses)

        # Set custom status
        await bot.change_presence(activity=nxt.CustomActivity(name=status))

        # Refresh custom status
        await asyncio.sleep(3600)

# Start Tempo
bot.run(beta_token)