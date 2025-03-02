from nextcord.ext import commands
from tokens import *
import nextcord


class Warning(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.prefix = "!"  # Old prefix

    @commands.Cog.listener()
    async def on_message(self, message):
        # Ignore bot messages and DMs
        if message.author.bot or not message.guild:
            return

        # Check if message starts with old prefix
        if message.content.startswith(self.prefix):
            embed = nextcord.Embed(color=nextcord.Color.from_rgb(134, 194, 50))
            embed.title = "Prefix Commands Are No Longer Supported"
            embed.description = (
                "Tempo now uses slash commands instead of prefix commands.\n\n"
                "**Users:** You can type `/` in chat and select Tempo to see a list of all available commands.\n\n"
                "**Admins:** If you haven't already done so, you'll need to reinvite Tempo to enable slash commands. Simply click the link below.\n\n"
                f"[Click Here to Invite Tempo]({tempo_invite_link})"
            )
            embed.set_thumbnail(url="https://raw.githubusercontent.com/hexxzn/tempo/refs/heads/main/resources/logo-transparent.png")

            # Send message as ephemeral so only user sees it
            await message.channel.send(f"{message.author.mention}", embed=embed)

            # Delete user message to prevent confusion
            try:
                await message.delete()
            except nextcord.errors.Forbidden:
                pass  # Bot doesn't have permission to delete messages, so ignore


def setup(bot):
    bot.add_cog(Warning(bot))