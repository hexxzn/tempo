import nextcord
import nextcord.ext.commands as cmd
import logging
import asyncio
import random
from tokens import *

# Set the logging level for nextcord state and http to ERROR so that EXPECTED Forbidden warnings are suppressed.
logging.getLogger("nextcord.state").setLevel(logging.ERROR)
logging.getLogger("nextcord.http").setLevel(logging.ERROR)

intents = nextcord.Intents.default()
intents.message_content = True
intents.members = True

bot = cmd.Bot(intents=intents)

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
            try:
                await bot.sync_all_application_commands()
            except nextcord.Forbidden:
                print("Error: Not member of guild.")
            else:
                print("Slash commands synced successfully...")

    except Exception as e:
        print(f"Error during bot startup: {e}")

    print("Tempo is online.\n")

    statuses = [
        "Song request? Fire away!", 
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
        "You up…?"
    ]

    # Dynamic, periodically updated status message loop
    while True:
        status = random.choice(statuses)
        try:
            await bot.change_presence(activity=nextcord.CustomActivity(name=status))
        except nextcord.Forbidden:
            pass
        await asyncio.sleep(3600)

bot.run(beta_token)