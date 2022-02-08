from nextcord.ext import commands
from apikeys import *
import nextcord

bot = commands.Bot(command_prefix = '!', help_command = None)

@bot.event
async def on_ready():
    bot.load_extension('cogs.music')
    await bot.change_presence(activity=nextcord.Game(name="!help"))
    print(f'{bot.user} is online.')
    print('--------------------')

# @client.slash_command(guild_ids=[897862146422104065])
# async def main_test(interaction: nextcord.Interaction, message):
#     await interaction.response.send_message(message)

bot.run(tempo_token)