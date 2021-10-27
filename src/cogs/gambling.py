from os import name
from discord import message
from discord.ext import commands
from random import random
from random import seed
import locale
import math
import yaml

bot = commands.Bot(command_prefix = '!')
locale.setlocale(locale.LC_ALL, '')
seed()

with open(r'./bank.yaml') as file:
    bank = yaml.load(file, Loader=yaml.FullLoader)
with open(r'./wagers.yaml') as file:
    wagers = yaml.load(file, Loader=yaml.FullLoader)

class Dice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='balance')
    async def balance(self, ctx):
        """- Check your balance"""
        p1_id = ctx.author.id   # player id
        p1_name = ctx.author.name   # player name

        if p1_id not in bank:   # if player not in bank
            bank[p1_id] = {}
            bank[p1_id]['name'] = p1_name
            bank[p1_id]['balance'] = 0
            with open(r'./bank.yaml', 'w') as file: yaml.dump(bank, file)

        if p1_name != bank[p1_id]['name']:   # if player name does not match name in bank
            bank[p1_id]['name'] = p1_name
            with open(r'./bank.yaml', 'w') as file: yaml.dump(bank, file)

        await ctx.send("<@" + str(p1_id) + "> **You have " + f"{bank[p1_id]['balance']:,}" + " coins.**")

    @commands.command(name='wager')
    async def wager(self, ctx, coins=None):
        """- Offer a wager"""
        p1_id = ctx.author.id   # player id
        p1_name = ctx.author.name   # player name

        try:   # try to convert user input (coins) to integer
            coins = coins.replace('k', '000')   # replace k with 000
            coins = coins.replace('K', '000')   # replace K with 000
            coins = coins.replace(',', '')   # remove commas
            wager = int(coins) # convert formatted string (coins) to int (wager)
        
        except Exception as error:   # if input cannot be converted
            print(error)
            return await ctx.send("<@" + str(p1_id) + "> **Invalid wager.**" + "\n" + "Type **!wager <coins>** to place a wager.")

        if p1_id not in bank:   # if player not in bank
            bank[p1_id] = {}
            bank[p1_id]['name'] = p1_name
            bank[p1_id]['balance'] = 0
            with open(r'./bank.yaml', 'w') as file: yaml.dump(bank, file)

        if p1_name != bank[p1_id]['name']:   # if player name does not match name in bank
            bank[p1_id]['name'] = p1_name
            with open(r'./bank.yaml', 'w') as file: yaml.dump(bank, file)

        if p1_id in wagers:   # if player already has active wager
            try:
                bot_msg_id = await ctx.fetch_message(wagers[p1_id]['bot_message'])
                user_msg_id = await ctx.fetch_message(wagers[p1_id]['user_message'])
                await bot_msg_id.delete()
                await user_msg_id.delete()
            
            except Exception as error:
                print("Message already deleted")

            wagers.pop(p1_id)
            with open(r'./wagers.yaml', 'w') as file: yaml.dump(wagers, file)

        if wager > bank[p1_id]['balance']:   # if wager is greater than user's available balance
            await ctx.send("<@" + str(p1_id) + "> **Insufficient funds. Type !balance to check your balance.**")
        
        elif wager < 1:   # if wager is less than 1
            await ctx.send("<@" + str(p1_id) + "> **Wager cannot be less than one coin.**")
        
        else:   # place wager
            wagers[p1_id] = {}
            wagers[p1_id]['wager'] = wager
            wagers[p1_id]['user_name'] = p1_name
            with open(r'./wagers.yaml', 'w') as file: yaml.dump(wagers, file)

            wager_message = await ctx.send("🪙  " + "<@" + str(p1_id) + "> **wagers " + f"{wagers[p1_id]['wager']:,}" + " coins.**" + "\n" + "🪙  " + "Type **!accept " + str(p1_id) + "** to accept.")
            wagers[p1_id]['user_message'] = ctx.message.id
            wagers[p1_id]['bot_message'] = wager_message.id
            with open(r'./wagers.yaml', 'w') as file: yaml.dump(wagers, file)

    @commands.command(name='accept')
    async def accept(self, ctx, wager_id):
        """- Accept a wager"""
        if int(wager_id) not in wagers:
            await ctx.send("<@" + str(ctx.author.id) + "> **Invalid wager code.**")
            return
        
        p1_id = int(wager_id)
        p1_name = wagers[p1_id]['user_name']
        p2_id = ctx.author.id
        p2_name = ctx.author.name

        if p2_id not in bank:   # if player not in bank
            bank[p2_id] = {}
            bank[p2_id]['name'] = p2_name
            bank[p2_id]['balance'] = 0
            with open(r'./bank.yaml', 'w') as file: yaml.dump(bank, file)

        if p2_name != bank[p2_id]['name']:   # if player name does not match name in bank
            bank[p2_id]['name'] = p2_name
            with open(r'./bank.yaml', 'w') as file: yaml.dump(bank, file)

        if wagers[p1_id]['wager'] > bank[p2_id]['balance']:   # if wager is greater than user's available balance
            await ctx.send("<@" + str(p2_id) + "> **Insufficient funds. Type !balance to check your balance.**")
        
        else:
            async def wager_roll():
                p1_roll_one = math.ceil(random() * 6)
                p1_roll_two = math.ceil(random() * 6)
                p1_total = p1_roll_one + p1_roll_two
                p2_roll_one = math.ceil(random() * 6)
                p2_roll_two = math.ceil(random() * 6)
                p2_total = p2_roll_one + p2_roll_two

                if p1_total != p2_total and p1_total > p2_total:
                    await ctx.send("<@" + str(p2_id) + "> **accepted " + "<@" + str(p1_id) + ">'s wager of " + f"{wagers[p1_id]['wager']:,}" + " coins.**" + "\n" +
                                p1_name + ": " + "[" + str(p1_roll_one) + "]" + "[" + str(p1_roll_two) + "]" + " - " + str(p1_total) + "\n" +
                                p2_name + ": " + "[" + str(p2_roll_one) + "]" + "[" + str(p2_roll_two) + "]" + " - " + str(p2_total) + "\n" +
                                "**" + p1_name + " wins " + f"{wagers[p1_id]['wager']:,}" + " coins!**")

                    bank[p2_id]['balance'] -= wagers[p1_id]['wager']
                    bank[p1_id]['balance'] += wagers[p1_id]['wager']

                    # wager_create_user_message = await ctx.fetch_message(wagers[p1_id]['user_message'])
                    # wager_accept_user_message = await ctx.fetch_message(ctx.message.id)
                    wager_create_bot_message = await ctx.fetch_message(wagers[p1_id]['bot_message'])
                    # await wager_create_user_message.delete()
                    # await wager_accept_user_message.delete()
                    await wager_create_bot_message.delete()

                    wagers.pop(p1_id)
                    with open(r'./wagers.yaml', 'w') as file: yaml.dump(wagers, file)
                    with open(r'./bank.yaml', 'w') as file: yaml.dump(bank, file)

                elif p1_total != p2_total and p1_total < p2_total:
                    await ctx.send("<@" + str(p2_id) + "> **accepted " + "<@" + str(p1_id) + ">'s wager of " + f"{wagers[p1_id]['wager']:,}" + " coins.**" + "\n" +
                                p1_name + ": " + "[" + str(p1_roll_one) + "]" + "[" + str(p1_roll_two) + "]" + " - " + str(p1_total) + "\n" +
                                p2_name + ": " + "[" + str(p2_roll_one) + "]" + "[" + str(p2_roll_two) + "]" + " - " + str(p2_total) + "\n" +
                                "**" + p2_name + " wins " + f"{wagers[p1_id]['wager']:,}" + " coins!**")

                    bank[p1_id]['balance'] -= wagers[p1_id]['wager']
                    bank[p2_id]['balance'] += wagers[p1_id]['wager']

                    # wager_create_user_message = await ctx.fetch_message(wagers[p1_id]['user_message'])
                    # wager_accept_user_message = await ctx.fetch_message(ctx.message.id)
                    wager_create_bot_message = await ctx.fetch_message(wagers[p1_id]['bot_message'])
                    # await wager_create_user_message.delete()
                    # await wager_accept_user_message.delete()
                    await wager_create_bot_message.delete()

                    wagers.pop(p1_id)
                    with open(r'./wagers.yaml', 'w') as file: yaml.dump(wagers, file)
                    with open(r'./bank.yaml', 'w') as file: yaml.dump(bank, file)

                else:
                    await wager_roll()

            await wager_roll()

    @commands.command(name='roll')
    async def roll(self, ctx):
        """- Roll for free"""
        p1_name = ctx.author.name
        p1_id = ctx.author.id
        p1_roll_one = math.ceil(random() * 6)
        p1_roll_two = math.ceil(random() * 6)
        p1_total = p1_roll_one + p1_roll_two

        await ctx.send("<@" + str(p1_id) + "> **rolls the dice.**" + "\n" +
                       p1_name + ": " + "[" + str(p1_roll_one) + "]" + "[" + str(p1_roll_two) + "]" + " - " + str(p1_total))
        
    @commands.command(name='cancel')
    async def cancel(self, ctx):
        """- Cancel your wager"""
        if ctx.author.id in wagers:
            wager_create_bot_message = await ctx.fetch_message(wagers[ctx.author.id]['bot_message'])
            await wager_create_bot_message.delete()
            wagers.pop(ctx.author.id)
            with open(r'./wagers.yaml', 'w') as file: yaml.dump(wagers, file)
            await ctx.send("<@" + str(ctx.author.id) + "> **Your wager has been canceled.**")
        else:
            await ctx.send("<@" + str(ctx.author.id) + "> **You don't have an active wager.**")

    @commands.command(name='duel')
    async def duel(self, ctx):
        """- Challenge user to a dice duel"""
        
def setup(bot):
    bot.add_cog(Dice(bot))