from nextcord import Interaction, slash_command, SelectOption
from nextcord.ext import commands as cmd
import nextcord as nxt


class Help(cmd.Cog):
    def __init__(self, bot):
        self.bot = bot

    @slash_command(description="Select from a list of commands for additional info on what the command does and how to use it.", guild_ids=[949642805138059285])
    async def help(self, interaction: Interaction):

        # Help embed with thumbnail
        help_menu = nxt.Embed(color=nxt.Color.from_rgb(134, 194, 50))
        help_menu.title = "Help Menu"
        help_menu.description = "Select a command from the dropdown below to view details."
        help_menu.set_thumbnail(url="https://your-bot-image-link.com/logo.png")

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
                    "play": "**Command: Play**\nPlay a song or add it to the queue.\n\n**Syntax**\n`/play <song title>`\n`/play <youtube video link>`\n`/play <youtube playlist link>`",
                    "stop": "**Command: Stop**\nStop playback, clear the queue, and disconnect.",
                    "pause": "**Command: Pause**\nPause playback.",
                    "resume": "**Command: Resume**\nResume playback.",
                    "skip": "**Command: Skip**\nSkip the current song.",
                    "restart": "**Command: Restart**\nRestart the current song.",
                    "seek": "**Command: Seek**\nSeek to a position in the current song.\n\n**Syntax**\n`/seek <seconds>`",
                    "song": "**Command: Song**\nGet the title of the current song.",
                    "queue": "**Command: Queue**\nShow the song queue.",
                    "repeat": "**Command: Repeat**\nToggle repeat mode.",
                    "shuffle": "**Command: Shuffle**\nToggle shuffle mode.",
                    "remove": "**Command: Remove**\nRemove a song from the queue.\n\n**Syntax**\n`/remove <track number>`",
                    "volume": "**Command: Volume**\nAdjust playback volume.\n\n**Syntax**\n`/volume <1-100>`",
                    "search": "**Command: Search**\nSearch for a song before playing.\n\n**Syntax**\n`/search <song title>`",
                }

                embed = nxt.Embed(color=nxt.Color.from_rgb(134, 194, 50))
                embed.description = command_help[selected_command]
                embed.set_thumbnail(url="https://your-bot-image-link.com/logo.png")  # Keeps thumbnail in responses

                await interaction.response.edit_message(embed=embed)  # Dropdown remains for multiple selections

        # Create a view for the dropdown
        view = nxt.ui.View()
        view.add_item(HelpDropdown())

        # Send message with dropdown menu
        await interaction.response.send_message(embed=help_menu, view=view)

# Add cog
def setup(bot):
    bot.add_cog(Help(bot))
