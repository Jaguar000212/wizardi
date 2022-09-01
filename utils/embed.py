import disnake
import time
import datetime


def Embed(bot, ctx, footer):
    embed = disnake.Embed()
    embed.set_author(name=bot.user.display_name, icon_url=bot.user.avatar)
    embed.set_footer(
        text=f"{footer} by {ctx.author.display_name}",
        icon_url=ctx.author.display_avatar.url,
    )

    return embed


def logEmbed(bot, ctx, action, detail, guilty: disnake.Member, mod: disnake.Member):
    hour = time.time()
    stamp = datetime.datetime.fromtimestamp(hour).strftime("%Y-%m-%d %H:%M:%S")
    embed = disnake.Embed(title=action, description=detail, color=16711680)
    embed.add_field(name="Evidence", value=ctx.content, inline=False)
    embed.add_field(name="Guilty", value=guilty.mention, inline=True)
    embed.add_field(name="Channel", value=f"<#{str(ctx.channel.id)}>", inline=True)
    embed.add_field(name="Time", value=stamp, inline=True)
    embed.add_field(name="Moderator", value=mod.display_name, inline=True)
    embed.set_author(name=bot.user.display_name, icon_url=f"{bot.user.avatar.url}")
    embed.set_footer(text=f"Punished by {mod.display_name}")
    return embed
