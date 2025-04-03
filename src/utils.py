import nextcord

def tempo_embed(description=""):
    embed = nextcord.Embed(color=nextcord.Color.from_rgb(134, 194, 50))
    if description:
        embed.description = description
    return embed

def dynamic_slash_command(*args, **kwargs):
    from tokens import development_mode, tempo_guild_ids

    if development_mode:
        kwargs["guild_ids"] = tempo_guild_ids
    return nextcord.slash_command(*args, **kwargs)