import disnake
from disnake.ext import commands
from disnake.ui import Button, View
import datetime as dt
from disnake.ext.commands.params import Param

from bot import Bot


class Censor(commands.Cog):
    """
    For your friendly environment
    """

    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.guild_only()
    @commands.slash_command(description="To toggle censoring")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    @commands.cooldown(1, 30, commands.BucketType.guild)
    async def censor(self, ctx: disnake.AppCmdInter):
        await ctx.response.defer()
        embed = disnake.Embed(
            title="Censor",
            description=f"{self.bot.icons['warning']} Select whether to turn censoring on or off!",
            color=16098851,
            timestamp=dt.datetime.now(dt.timezone.utc),
        )
        embed.set_author(
            name=self.bot.user.display_name, icon_url=f"{self.bot.user.avatar.url}"
        )
        embed.set_footer(
            text=f"Requested by {ctx.author.display_name}",
            icon_url=ctx.author.display_avatar.url,
        )

        view = View(timeout=10)
        style = disnake.ButtonStyle
        item = Button

        on = item(
            style=style.green,
            label="Turn On!",
            custom_id="on",
            emoji=f"{self.bot.icons['tick']}",
        )
        off = item(
            style=style.red,
            label="Turn Off!",
            custom_id="off",
            emoji=f"{self.bot.icons['cross']}",
        )
        view.add_item(item=on)
        view.add_item(item=off)
        await ctx.send(embed=embed, view=view)

        async def on_callback(interaction):
            if interaction.user != ctx.author:
                await interaction.response.send_message(
                    "This isn't requested by you!", ephemeral=True
                )
            else:
                await interaction.response.defer()
                embed = disnake.Embed(
                    title="Censoring ON!",
                    description=f"{self.bot.icons['enable']} Watching on your words! Mind them",
                    color=65389,
                    timestamp=dt.datetime.now(dt.timezone.utc),
                )
                embed.set_author(
                    name=self.bot.user.display_name,
                    icon_url=f"{self.bot.user.avatar.url}",
                )
                embed.set_footer(
                    text=f"Toggled by {ctx.author.display_name}",
                    icon_url=ctx.author.display_avatar.url,
                )

                if not await self.bot.censorBot.censor(ctx=ctx):
                    await self.bot.BotDB.updateCensor(str(ctx.guild.id), True)
                    await ctx.edit_original_message(embed=embed)
                else:
                    await ctx.edit_original_message(
                        "",
                        embed=disnake.Embed(
                            description=f"{self.bot.icons['redtick']} Censoring is already on...",
                            color=disnake.Colour.yellow(),
                        ),
                    )

        async def off_callback(interaction):
            if interaction.user != ctx.author:
                await interaction.response.send_message(
                    "This isn't requested by you!", ephemeral=True
                )
            else:
                await interaction.response.defer()
                embed = disnake.Embed(
                    title="Censoring OFF!",
                    description=f"{self.bot.icons['disable']} No more warns... Feel the RIGHT TO SPEECH!",
                    color=16712965,
                    timestamp=dt.datetime.now(dt.timezone.utc),
                )
                embed.set_author(
                    name=self.bot.user.display_name,
                    icon_url=f"{self.bot.user.avatar.url}",
                )
                embed.set_footer(
                    text=f"Toggled by {ctx.author.display_name}",
                    icon_url=ctx.author.display_avatar.url,
                )

                if await self.bot.censorBot.censor(ctx=ctx):
                    await self.bot.BotDB.updateCensor(str(ctx.guild.id), False)
                    await ctx.edit_original_message(embed=embed)
                else:
                    await ctx.edit_original_message(
                        "",
                        embed=disnake.Embed(
                            description=f"{self.bot.icons['redtick']} Censoring is already off... You NOOB!",
                            color=disnake.Colour.yellow(),
                        ),
                    )

        async def on_timeout(self=view):
            for button in self.children:
                button.disabled = True
            await ctx.edit_original_message(view=view)

        view.timeout = 10
        view.on_timeout = on_timeout
        on.callback = on_callback
        off.callback = off_callback

    @commands.guild_only()
    @commands.slash_command(name = "censor-blist", description="To manage blacklist")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def blist(self, ctx: disnake.AppCmdInter):
        pass

    @commands.cooldown(1, 30, commands.BucketType.guild)
    @blist.sub_command(description="To show blacklist")
    async def show(ctx: disnake.AppCmdInter):
        blacklist = await ctx.bot.censorBot.blacklist(ctx=ctx)

        if len(blacklist) != 0:
            blacklist = "\n".join(map(str, blacklist))
            blacklist = f"||{blacklist}||"
            embed = disnake.Embed(
                title="Blacklist",
                description=f"Blacklist for **{ctx.guild.name}**",
                color=53759,
                timestamp=dt.datetime.now(dt.timezone.utc),
            )
            embed.add_field(name="List -", value=blacklist, inline=True)
            embed.set_author(
                name=ctx.bot.user.display_name, icon_url=f"{ctx.bot.user.avatar.url}"
            )
            embed.set_footer(
                text=f"Requested by {ctx.author.display_name}",
                icon_url=ctx.author.display_avatar.url,
            )
            await ctx.send(embed=embed, ephemeral=True)
        else:
            await ctx.send(
                embed=disnake.Embed(
                    description=f"{ctx.bot.icons['info']} There is no blacklist! Start by adding one",
                    color=disnake.Colour.yellow(),
                ),
                delete_after=4,
            )

    @commands.cooldown(1, 30, commands.BucketType.guild)
    @blist.sub_command(description="To add a word to blacklist")
    async def add(
        ctx: disnake.AppCmdInter, word=Param(description="Word to be appended")
    ):
        await ctx.response.defer()
        Word = word.lower()
        if not await ctx.bot.BotDB.updateBlackList(str(ctx.guild.id), Word, "append"):
            embed = disnake.Embed(
                description=f"{ctx.bot.icons['failed']} **`{Word}`** is already in the blacklist",
                color=disnake.Colour.red(),
            )
            await ctx.send(embed=embed, delete_after=4)
        else:
            embed = disnake.Embed(
                title="Success",
                description=f"{ctx.bot.icons['passed']} A new word, **`{Word}`**, has been added to the blacklist and I will be watching over it!",
                color=16712965,
            )
            embed.set_author(
                name=ctx.bot.user.display_name, icon_url=f"{ctx.bot.user.avatar.url}"
            )
            embed.set_footer(
                text=f"Configured by {ctx.author.display_name}",
                icon_url=ctx.author.display_avatar.url,
            )
            await ctx.send(embed=embed)

    @commands.cooldown(1, 30, commands.BucketType.guild)
    @blist.sub_command(description="To drop a word from blacklist")
    async def drop(
        ctx: disnake.AppCmdInter, word=Param(description="Word to be removed")
    ):
        await ctx.response.defer()
        Word = word.lower()
        if not await ctx.bot.BotDB.updateBlackList(str(ctx.guild.id), Word, "pop"):
            embed = disnake.Embed(
                description=f"{ctx.bot.icons['failed']} **`{Word}`** is not in the blacklist",
                color=disnake.Colour.red(),
            )
            await ctx.send(embed=embed, delete_after=4)
        else:
            embed = disnake.Embed(
                title="Success",
                description=f"{ctx.bot.icons['passed']} **`{Word}`** has been removed from the blacklist!",
                color=65353,
            )
            embed.set_author(
                name=ctx.bot.user.display_name, icon_url=f"{ctx.bot.user.avatar.url}"
            )
            embed.set_footer(
                text=f"Configured by {ctx.author.display_name}",
                icon_url=ctx.author.display_avatar.url,
            )
            await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.slash_command(name = "censor-wlist", description="To manage whitelist")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def wlist(self, ctx: disnake.AppCmdInter):
        pass

    @commands.cooldown(1, 30, commands.BucketType.guild)
    @wlist.sub_command(name="show", description="To show whitelist")
    async def _show(ctx: disnake.AppCmdInter):
        whitelist = await ctx.bot.censorBot.whitelist(ctx=ctx)
        if len(whitelist) != 0:
            whitelist = "\n".join(map(str, whitelist))
            whitelist = f"||{whitelist}||"
            embed = disnake.Embed(
                title="Whitelist",
                description=f"Whitelist for **{ctx.guild.name}**",
                color=53759,
                timestamp=dt.datetime.now(dt.timezone.utc),
            )
            embed.add_field(name="List -", value=whitelist, inline=True)
            embed.set_author(
                name=ctx.bot.user.display_name, icon_url=f"{ctx.bot.user.avatar.url}"
            )
            embed.set_footer(
                text=f"Requested by {ctx.author.display_name}",
                icon_url=ctx.author.display_avatar.url,
            )
            await ctx.send(embed=embed, ephemeral=True)
        else:
            await ctx.send(
                embed=disnake.Embed(
                    description=f"{ctx.bot.icons['info']} There is no whitelist! Start by adding one",
                    color=disnake.Colour.yellow(),
                ),
                delete_after=4,
            )

    @commands.cooldown(1, 30, commands.BucketType.guild)
    @wlist.sub_command(name="add", description="To add a word to whitelist")
    async def _add(
        ctx: disnake.AppCmdInter, word=Param(description="Word to be appended")
    ):
        await ctx.response.defer()
        Word = word.lower()
        if not await ctx.bot.BotDB.updateWhiteList(str(ctx.guild.id), Word, "append"):
            msg_wold = disnake.Embed(
                description=f"{ctx.bot.icons['failed']} **`{Word}`** is already in the whitelist",
                color=disnake.Colour.red(),
            )
            await ctx.send(embed=msg_wold, delete_after=4)
        else:
            embed = disnake.Embed(
                title="Success",
                description=f"{ctx.bot.icons['passed']} A new word, **`{Word}`**, has been added to the whitelist!",
                color=65353,
            )
            embed.set_author(
                name=ctx.bot.user.display_name, icon_url=f"{ctx.bot.user.avatar.url}"
            )
            embed.set_footer(
                text=f"Configured by {ctx.author.display_name}",
                icon_url=ctx.author.display_avatar.url,
            )
            await ctx.send(embed=embed)

    @commands.cooldown(1, 30, commands.BucketType.guild)
    @wlist.sub_command(name="drop", description="To drop a word from whitelist")
    async def _drop(
        ctx: disnake.AppCmdInter, word=Param(description="Word to be removed")
    ):
        await ctx.response.defer()
        Word = Word.lower()
        if not await ctx.bot.BotDB.updateWhiteList(str(ctx.guild.id), Word, "pop"):
            embed = disnake.Embed(
                description=f"{ctx.bot.icons['failed']} **`{Word}`** is not in the whitelist",
                color=disnake.Colour.red(),
            )
            await ctx.send(embed=embed, delete_after=4)
        else:
            embed = disnake.Embed(
                title="Success",
                description=f"{ctx.bot.icons['passed']} **`{Word}`** has been removed from the whitelist!",
                color=65353,
            )
            embed.set_author(
                name=ctx.bot.user.display_name, icon_url=f"{ctx.bot.user.avatar.url}"
            )
            embed.set_footer(
                text=f"Configured by {ctx.author.display_name}",
                icon_url=ctx.author.display_avatar.url,
            )
            await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.slash_command(name = "censor-wchannel", description="To manage white channel list")
    @commands.has_permissions(manage_messages=True, manage_channels=True)
    @commands.bot_has_permissions(manage_messages=True, manage_channels=True)
    async def wchannel(self, ctx: disnake.AppCmdInter):
        pass

    @commands.cooldown(1, 30, commands.BucketType.guild)
    @wchannel.sub_command(name="show", description="To show whitelist")
    async def __show(self, ctx: disnake.AppCmdInter):
        channelist = await self.bot.censorBot.whitechannel(ctx=ctx)
        if len(channelist) != 0:
            channelist = ["<#" + channels + ">" for channels in channelist]
            channelist = "\n\n".join(map(str, channelist))
            embed = disnake.Embed(
                title="Whitelisted Channels",
                color=53759,
                timestamp=dt.datetime.now(dt.timezone.utc),
            )
            embed.add_field(name="List -", value=channelist, inline=True)
            embed.set_author(
                name=ctx.bot.user.display_name, icon_url=f"{ctx.bot.user.avatar.url}"
            )
            embed.set_footer(
                text=f"Requested by {ctx.author.display_name}",
                icon_url=ctx.author.display_avatar.url,
            )
            await ctx.send(embed=embed, ephemeral=True)
        else:
            await ctx.send(
                embed=disnake.Embed(
                    description=f"{ctx.bot.icons['info']} No channel is whitelisted! Start by adding one",
                    color=disnake.Colour.yellow(),
                ),
                delete_after=4,
            )

    @commands.cooldown(1, 30, commands.BucketType.guild)
    @wchannel.sub_command(name="add", description="To add channel to whitelist")
    async def __add(
        self,
        ctx: disnake.AppCmdInter,
        channel: disnake.TextChannel = Param(
            description="Text Channel to exclude from censoring"
        ),
    ):
        await ctx.response.defer()
        channel_id = str(channel.id)
        if not await self.bot.BotDB.updateWhitechannelList(
            str(ctx.guild.id), channel_id, "append"
        ):
            embed = disnake.Embed(
                description=f"{ctx.bot.icons['failed']} {channel.mention} is already whitelisted",
                color=disnake.Colour.red(),
            )
            await ctx.send(embed=embed, delete_after=4)
        else:
            embed = disnake.Embed(
                title="Success",
                description=f"{ctx.bot.icons['passed']} {channel.mention}, has been whitelisted!",
                color=16712965,
            )
            embed.set_author(
                name=ctx.bot.user.display_name, icon_url=f"{ctx.bot.user.avatar.url}"
            )
            embed.set_footer(
                text=f"Configured by {ctx.author.display_name}",
                icon_url=ctx.author.display_avatar.url,
            )
            await ctx.send(embed=embed)

    @wchannel.sub_command(name="drop", description="To delete channel from whitelist")
    async def __drop(
        self, ctx: disnake.AppCmdInter, channel: disnake.TextChannel = Param()
    ):
        await ctx.response.defer()
        channel_id = str(channel.id)
        if not await self.bot.BotDB.updateWhitechannelList(
            str(ctx.guild.id), channel_id, "pop"
        ):
            embed = disnake.Embed(
                description=f"{ctx.bot.icons['failed']} {channel.mention} is not whitelisted",
                color=disnake.Colour.red(),
            )
            await ctx.send(embed=embed, delete_after=4)
        else:
            embed = disnake.Embed(
                title="Success",
                description=f"{ctx.bot.icons['passed']} {channel.mention} has been removed from whitelist!",
                color=65353,
            )
            embed.set_author(
                name=ctx.bot.user.display_name, icon_url=f"{ctx.bot.user.avatar.url}"
            )
            embed.set_footer(
                text=f"Configured by {ctx.author.display_name}",
                icon_url=ctx.author.display_avatar.url,
            )
            await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Censor(bot))
