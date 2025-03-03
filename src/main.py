from nextcord.ext import commands as cmd
import nextcord as nxt
from tokens import *
import asyncio
import random


intents = nxt.Intents.default()
intents.message_content = True

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

    statuses = ["Loading vibes…", 
                "Song request? Fire away!", 
                "Max volume. Ready?", 
                "Bangers incoming…", 
                "Music is my middle name.", 
                "I'm your DJ. What's up?", 
                "Tune in, vibe out.", 
                "Chill vibes on deck!",
                "Music on, world off.",
                "Did someone say 'remix'?",
                "Let's party!",
                "It's a vibe, trust me.",
                "Yo, pass me the aux.",
                "The music never sleeps.",
                "Jams: Now loading…",
                "Turn it up!",
                "One more song!",
                "Rock out w/ your bot out!",
                "Vibe check: You're good.",
                "Keep calm, music's here.",
                "This beat hits different…",
                "Bruh…",
                "Let's get it.",
                "It's lit!",
                "Let's get this bread.",
                "Let's gooooooo!",
                "We out here vibin.",
                "Straight fire…"]
    
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