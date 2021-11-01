from datetime import datetime as dt
from discord.ext import commands
from yahoo_fin import stock_info as si

bot = commands.Bot(command_prefix = '!')
quote = {}

def market_session():       # Determine current market session (premarket, live, postmarket)
    now = dt.now()
    current_time = now.strftime("%H:%M:%S")

    if current_time >= '04:00:00' and current_time < '09:30:00':
        return "premarket"
    elif current_time >= '09:30:00' and current_time < '16:00:00':
        return "live"
    elif current_time >= '16:00:00' and current_time < '20:00:00':
        return "postmarket"
    else:
        return "live"

class Stocks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='price')
    async def price(self, ctx, ticker):
        # now = dt.now()
        # current_time = now.strftime("%H:%M:%S")
        quote = si.get_quote_data(ticker)
        price = eval("si.get_" + market_session() + "_price(ticker)")
        await ctx.send("__**" + quote['shortName'] + "**__" + "\n" + "Live Price: $" + str(round(price, 2)) + "\n" + "")

def setup(bot):
    bot.add_cog(Stocks(bot))