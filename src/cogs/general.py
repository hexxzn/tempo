import nextcord
import nextcord.ext.commands as cmd
import subprocess
from decorators import log_calls, developer_only
from tokens import *


class General(cmd.Cog):
    def __init__(self, bot):
        self.bot = bot

    @log_calls
    @developer_only
    @nextcord.slash_command(description="[Developer Only] Cross-server diagnostic info.", guild_ids=tempo_guild_ids)
    async def status(self, interaction: nextcord.Interaction):
        # Iterate through each guild Tempo is a member of
        guild_list = []
        playing = 0
        for guild in self.bot.guilds:
            tempo = guild.get_member(self.bot.user.id)

            # If Tempo is not connected to a voice channel
            if tempo.voice is None:
                status_icon = "🔴"
            else:
                status_icon = "🟢"
                playing += 1

            # Add relevant info to guild list
            guild_info = {
                "status": status_icon,
                "guild_name": guild.name,
                "guild_owner": await self.bot.fetch_user(guild.owner_id),
                "join_date": tempo.joined_at,
                "join_date_string": tempo.joined_at.strftime("%m-%d-%y"),
            }
            guild_list.append(guild_info)

        # Create info string with guilds sorted by bot join date
        info_list = ''
        for guild_info in sorted(guild_list, key=lambda date: date["join_date"]):
            info_list += f'`{guild_info["status"]}` `[{guild_info["join_date_string"]}]` `{guild_info["guild_name"]}` `({guild_info["guild_owner"]})`\n'

        # Create embed and set border color
        embed = nextcord.Embed(color=nextcord.Color.from_rgb(134, 194, 50))
        embed.add_field(name=f'__Guilds Joined__', value=f'`{len(self.bot.guilds)}`', inline=True)
        embed.add_field(name=f'__Active Players__', value=f'`{playing}`', inline=True)
        embed.add_field(name=f'__Guild Details__', value=info_list, inline=False)

        # Send embed message (Ephemeral to keep it private)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @log_calls
    @developer_only
    @nextcord.slash_command(description="[Developer Only] Force reboot.", guild_ids=tempo_guild_ids)
    async def bash(self, interaction: nextcord.Interaction):
        # Defer the response immediately to avoid timeout
        await interaction.response.defer(ephemeral=True)
        try:
            result = subprocess.run(
                ["bash", "restart.sh"],
                cwd="/home/gkilburg_biz/git/tempo/src",  # set the correct working directory
                capture_output=True, 
                text=True,
                check=True  # Raise CalledProcessError if the command fails
            )
            # Won't execute if reboot is successful, but leaving this here for possible future use
            output = result.stdout.strip() or "No output."
            embed = nextcord.Embed(color=nextcord.Color.green())
            embed.title = "Restart Script Executed Successfully"
            embed.description = f"Output:\n```\n{output}\n```"
            await interaction.followup.send(embed=embed, ephemeral=True)
        except subprocess.CalledProcessError as e:
            error_output = e.stderr.strip() or str(e)
            embed = nextcord.Embed(color=nextcord.Color.red())
            embed.title = "Error Executing Restart Script"
            embed.description = f"Error Output:\n```\n{error_output}\n```"
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            embed = nextcord.Embed(color=nextcord.Color.red())
            embed.title = "Unexpected Error"
            embed.description = f"An unexpected error occurred:\n```\n{e}\n```"
            await interaction.followup.send(embed=embed, ephemeral=True)

    @log_calls
    @nextcord.slash_command(description="Get a link to invite the bot to another server.", guild_ids=tempo_guild_ids)
    async def invite(self, interaction: nextcord.Interaction):

        # Create and send embed
        embed = nextcord.Embed(color=nextcord.Color.from_rgb(134, 194, 50))
        embed.description = f"[Click Here to Invite Tempo]({tempo_invite_link})"

        await interaction.response.send_message(embed=embed)


def setup(bot):
    bot.add_cog(General(bot))