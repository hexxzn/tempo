import nextcord
import nextcord.ext.commands as cmd
from tokens import *


class Warning(cmd.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.prefix = "!"  # Old prefix

    # Notify user that bot no longer uses prefix commands
    @cmd.Cog.listener()
    async def on_message(self, message):
        # Ignore bot messages and DMs
        if message.author.bot or not message.guild:
            return

        # Check if message starts with old prefix
        if message.content.startswith(self.prefix):
            embed = nextcord.Embed(color=nextcord.Color.from_rgb(134, 194, 50))
            embed.title = "Prefix Commands Are No Longer Supported"
            embed.description = (
                "Tempo now uses slash commands instead of prefix commands.\n"
                "Instead of `!play` try `/play`\n\n"
                "**Users:** Type `/` in chat and select Tempo to see a list of all available commands.\n\n"
                "**Admins:** You'll need to kick and reinvite Tempo to enable slash commands.\n\n"
                f"[Click Here to Invite Tempo]({tempo_invite_link})"
            )
            embed.set_thumbnail(url="https://raw.githubusercontent.com/hexxzn/tempo/refs/heads/main/resources/logo-transparent.png")

            # Send the warning message
            await message.channel.send(f"{message.author.mention}", embed=embed)

            # Delete the user's message to prevent confusion
            try:
                await message.delete()
            except nextcord.errors.Forbidden:
                pass  # Bot doesn't have permission to delete the message

            return  # Stop further processing

        # Process other messages normally
        await self.bot.process_commands(message)


def setup(bot):
    bot.add_cog(Warning(bot))