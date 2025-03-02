from nextcord import Interaction, slash_command, SelectOption
from nextcord.ext import commands as cmd
import nextcord as nxt
from tokens import *


class Help(cmd.Cog):
    def __init__(self, bot):
        self.bot = bot

    @slash_command(description="Select from a list of commands for additional info on what the command does and how to use it.", guild_ids=tempo_guild_ids)
    async def help(self, interaction: Interaction):

        # Help embed with thumbnail
        help_menu = nxt.Embed(color=nxt.Color.from_rgb(134, 194, 50))
        help_menu.title = "Help Menu"
        help_menu.description = "Select a command from the dropdown below to view details.\n\n*The dropdown will disappear after 60 seconds of inactivity.*"
        help_menu.set_thumbnail(url="https://raw.githubusercontent.com/hexxzn/tempo/refs/heads/main/resources/logo-transparent.png")

        # Command descriptions (Dropdown options)
        command_descriptions = {
            "play": "Play a song or add it to the queue.",
            "stop": "Stop playback, clear the queue, and disconnect.",
            "pause": "Pause playback.",
            "resume": "Resume playback.",
            "skip": "Skip the current song.",
            "restart": "Restart the current song.",
            "seek": "Seek to a position in a song.",
            "song": "Get the title of the current song.",
            "queue": "Show the song queue.",
            "repeat": "Toggle repeat mode.",
            "shuffle": "Toggle shuffle mode.",
            "remove": "Remove a song from the queue.",
            "volume": "Adjust playback volume.",
            "search": "Search for a song before playing.",
        }

        # Create a dropdown menu
        class HelpDropdown(nxt.ui.Select):
            def __init__(self):
                options = [
                    SelectOption(label=cmd, description=desc, value=cmd)
                    for cmd, desc in command_descriptions.items()
                ]
                super().__init__(placeholder="Select a command...", options=options, min_values=1, max_values=1)

            async def callback(self, interaction: Interaction):
                selected_command = self.values[0]

                # Generate detailed help embed
                command_help = {
                    "play": "**Play**\nPlay a song or add it to the queue.\n\n**Syntax**\n`/play <song title and artist>`\n`/play <youtube video link>`\n`/play <youtube playlist link>`",
                    "stop": "**Stop**\nStop playback, clear the queue, and disconnect.\n\n**Syntax**\n`/stop`",
                    "pause": "**Pause**\nPause the current song.\n\n**Syntax**\n`/pause`",
                    "resume": "**Resume**\nResume the paused song.\n\n**Syntax**\n`/resume`",
                    "skip": "**Skip**\nSkip the current song.\n\n**Syntax**\n`/skip`",
                    "restart": "**Restart**\nRestart the current song.\n\n**Syntax**\n`/restart`",
                    "seek": "**Seek**\nSeek to a specific position in the current song.\n\n**Syntax**\n`/seek <seconds>`",
                    "song": "**Song**\nGet the title of the current song.\n\n**Syntax**\n`/song`",
                    "queue": "**Queue**\nGet a list of all songs in the queue.\n\n**Syntax**\n`/queue`",
                    "repeat": "**Repeat**\nToggle repeat mode for the current song.\n\n**Syntax**\n`/repeat`",
                    "shuffle": "**Shuffle**\nToggle shuffle mode for the queue.\n\n**Syntax**\n`/shuffle`",
                    "remove": "**Remove**\nRemove a song from the queue by its position.\n\n**Syntax**\n`/remove <queue number>`",
                    "volume": "**Volume**\nCheck current playback volume or adjust volume from 1 to 100.\nDefault volume is 20.\n\n**Syntax**\n`/volume`\n`/volume <1 - 100>`",
                    "search": "**Search**\nChoose from a list of songs.\n\n**Syntax**\n`/search <song title and artist>`",
                }

                embed = nxt.Embed(color=nxt.Color.from_rgb(134, 194, 50))
                embed.description = command_help[selected_command]
                embed.set_thumbnail(url="https://raw.githubusercontent.com/hexxzn/tempo/refs/heads/main/resources/logo-transparent.png")  # Keeps thumbnail in responses

                await interaction.response.edit_message(embed=embed)  # Dropdown remains for multiple selections

        # Create a view for the dropdown with timeout
        class HelpView(nxt.ui.View):
            def __init__(self):
                super().__init__(timeout=60)  # Timeout set to 60 seconds
                self.add_item(HelpDropdown())

            async def on_timeout(self):
                for child in self.children:
                    child.disabled = True  # Disable dropdown on timeout
                await self.message.edit(view=None)  # Remove dropdown from message

        view = HelpView()

        # Send message with dropdown menu
        message = await interaction.response.send_message(embed=help_menu, view=view, ephemeral=True)
        view.message = message  # Store message reference for timeout handling


# Add cog
def setup(bot):
    bot.add_cog(Help(bot))
