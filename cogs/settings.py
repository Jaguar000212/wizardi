import disnake
from disnake.ext import commands
import datetime as dt
from bot import Bot
from utils.helpers import EmojiPaginator
from disnake.ext.commands.params import Param


class Settings(commands.Cog):
    """
    Bot configurations (Must see)
    """

    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.guild_only()
    @commands.slash_command(name="config-log", description="Set a logging channel")
    @commands.cooldown(1, 30, commands.BucketType.guild)
    @commands.has_permissions(manage_guild=True)
    async def log(
        self,
        ctx: disnake.AppCmdInter,
        channel: disnake.TextChannel = Param(description="Logging Channel"),
    ):
        await ctx.response.defer()
        try:
            await channel.send(embed=disnake.Embed(description="Loggings enabled"))
        except:
            await ctx.send(
                embed=disnake.Embed(
                    description=f"Can't set {channel.mention} for loggings. No permissions to send mesaages there!"
                )
            )
            return
        channel_id = channel.id
        embed = disnake.Embed(
            title="Updated!",
            description=f"{self.bot.icons['check']} Loggings channel has been updated to {channel.mention}",
            color=65389,
            timestamp=dt.datetime.now(dt.timezone.utc),
        )
        embed.set_author(
            name=self.bot.user.display_name, icon_url=f"{self.bot.user.avatar.url}"
        )
        embed.set_footer(
            text=f"Configured by {ctx.author.display_name}",
            icon_url=ctx.author.display_avatar.url,
        )
        await self.bot.BotDB.updateLogChannel(
            str(ctx.guild.id), channelID=str(channel_id)
        )
        await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @commands.slash_command(
        name="config-chatbot", description="Toggle AI chatbot in your server"
    )
    @commands.cooldown(1, 30, commands.BucketType.guild)
    async def chatbot(
        self,
        ctx: disnake.AppCmdInter,
        channel: disnake.TextChannel = Param(
            None,
            description="Channel to enable ChatBot in"
        ),
    ):
        await ctx.response.defer()
        if channel is None:
            channel = ctx.channel
        try:
            await channel.send(".", delete_after=0.1)
        except:
            await ctx.send(
                embed=disnake.Embed(
                    description=f"Can't enable chatbot in {channel.mention}. No permissions to send mesaages there!"
                )
            )
            return
        if await self.bot.BotDB.updateChatbotChannel(channelID=channel.id):
            embed = disnake.Embed(
                title="ChatBot Enabled",
                description=f"{self.bot.icons['enable']} ChatBot has been enabled in {channel.mention}",
                color=53759,
            )
            embed.set_author(
                name=self.bot.user.display_name, icon_url=f"{self.bot.user.avatar.url}"
            )
            embed.set_footer(
                text=f"Requested by {ctx.author.display_name}",
                icon_url=ctx.author.display_avatar.url,
            )
            await channel.send(embed=disnake.Embed(description="Chatbot enabled"))
            await ctx.send(embed=embed)
        else:
            await self.bot.BotDB.updateChatbotChannel(
                channelID=channel.id, function="pop"
            )
            embed = disnake.Embed(
                title="ChatBot disabled",
                description=f"{self.bot.icons['disable']} ChatBot has been diabled in {channel.mention}",
                color=53759,
            )
            embed.set_author(
                name=self.bot.user.display_name, icon_url=f"{self.bot.user.avatar.url}"
            )
            embed.set_footer(
                text=f"Requested by {ctx.author.display_name}",
                icon_url=ctx.author.display_avatar.url,
            )
            await channel.send(embed=disnake.Embed(description="Chatbot disabled"))
            await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.slash_command(
        name="config-nqn",
        description="NQN options",
        invoke_without_command=True,
    )
    async def nqn(self, ctx: disnake.AppCmdInter):
        await ctx.response.defer()
        pass

    @commands.guild_only()
    @nqn.sub_command(description="Toggle NQN in the server")
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_guild_permissions(manage_messages=True, use_external_emojis=True)
    @commands.cooldown(1, 30, commands.BucketType.guild)
    async def toggle(self, ctx: disnake.AppCmdInter):
        if not await self.bot.BotDB.updateNQN(str(ctx.guild.id), False):
            await self.bot.BotDB.updateNQN(str(ctx.guild.id), True)
            embed = disnake.Embed(
                title="NQN Enabled",
                description=f"{self.bot.icons['enable']} NQN has been enabled in the server",
                color=53759,
            )
            embed.set_author(
                name=self.bot.user.display_name, icon_url=f"{self.bot.user.avatar.url}"
            )
            embed.set_footer(
                text=f"Requested by {ctx.author.display_name}",
                icon_url=ctx.author.display_avatar.url,
            )
            await ctx.send(embed=embed)
        else:
            embed = disnake.Embed(
                title="NQN disabled",
                description=f"{self.bot.icons['disable']} NQN has been diabled in the server",
                color=53759,
            )
            embed.set_author(
                name=self.bot.user.display_name, icon_url=f"{self.bot.user.avatar.url}"
            )
            embed.set_footer(
                text=f"Requested by {ctx.author.display_name}",
                icon_url=ctx.author.display_avatar.url,
            )
            await ctx.send(embed=embed)

    @commands.cooldown(1, 30, commands.BucketType.guild)
    @nqn.sub_command(description="All usable NQN emojis")
    async def emojis(self, ctx: disnake.AppCmdInter):
        animated = []
        static = []
        for emoji in self.bot.emojis:
            if emoji.animated:
                animated.append(f"{str(emoji)}")
            else:
                static.append(f"{str(emoji)}")
        await EmojiPaginator(ctx, animated, static).start()

    @commands.slash_command(description="Check Bot's latency")
    async def ping(self, ctx: disnake.AppCmdInter):
        await ctx.response.defer()
        embed = disnake.Embed(
            title="Pong!",
            description=f"{self.bot.icons['stats']} Current Latency - **{round (self.bot.latency * 1000)}ms**",
            color=65389,
            timestamp=dt.datetime.now(dt.timezone.utc),
        )
        embed.set_author(
            name=self.bot.user.display_name, icon_url=f"{self.bot.user.avatar.url}"
        )
        embed.set_footer(
            text=f"Requested by {ctx.author.display_name}",
            icon_url=ctx.author.display_avatar.url,
        )
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Settings(bot))
