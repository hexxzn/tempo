import nextcord

def tempo_embed(description=""):
    embed = nextcord.Embed(color=nextcord.Color.from_rgb(134, 194, 50))
    if description:
        embed.description = description
    return embed