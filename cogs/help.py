import disnake
from disnake.ext import commands
import datetime as dt

import disnake
from disnake.ext import commands
from disnake.errors import Forbidden
import sys
from utils.exceptions import NSFWChannel
from wavelink import Player
from utils.helpers import BotInformationView, CogEmoji
import topgg
from disnake.ext.commands.params import Param

from bot import Bot


async def send_embed(ctx, embed):
    try:
        await ctx.send(embed=embed)
    except Forbidden:
        try:
            await ctx.send(
                "Hey, seems like I can't send embeds. Please check my permissions :)"
            )
        except Forbidden:
            await ctx.author.send(
                f"Hey, seems like I can't send any message in {ctx.channel.name} on {ctx.guild.name}\n"
                f"May you inform the server team about this issue? :slight_smile: ",
                embed=embed,
            )


class Help(commands.Cog):
    """
    For this simple help!
    """

    def __init__(self, bot: Bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.topgg_webhook = topgg.WebhookManager(self.bot).dbl_webhook(
            "/dblwebhook", "password"
        )

        self.bot.topgg_webhook.run(5000)
        # self.bot.topggpy = topgg.DBLClient(self.bot.config.topgg,
        #                                    dbl_token,
        #                                    autopost=True,
        #                                    post_shard_count=True)

    @commands.guild_only()
    @commands.slash_command(description="For your simple help")
    async def help(
        self,
        ctx: disnake.AppCmdInter,
        input=Param(None, description="Command or module"),
    ):
        await ctx.response.defer()
        if input is None:
            modules = ""
            menu = disnake.ui.Select(placeholder="Select a module")
            view = disnake.ui.View(timeout=15)
            view.add_item(item=menu)
            embed = disnake.Embed(
                title="Welcome :tada:",
                description=f"Heya! {ctx.author.mention}. Welcome to **{self.bot.user.display_name}**, a helper bot with some useful commands!\n\nThis is the Help Desk for Wizardi.\nAlso, try /info for bot's information```fix\n\n <> - Required | [] - Optional | () - Default```",
                color=14667786,
            )
            embed.set_author(
                name=self.bot.user.display_name, icon_url=self.bot.user.avatar.url
            )
            embed.set_footer(
                text=f"Requested by {ctx.author.display_name}",
                icon_url=ctx.author.display_avatar.url,
            )
            for cog in self.bot.cogs:
                if cog == "Message" or cog == "Help":
                    continue
                modules += f"> \{CogEmoji[cog]} **{cog}**\n"
                cogs = self.bot.get_cog(cog)
                menu.add_option(
                    label=cog, description=cogs.description, emoji=CogEmoji[cog]
                )

            embed.add_field(name="Modules :-", value=modules)

            async def callback(interaction):
                if interaction.user != ctx.author:
                    await interaction.response.send_message(
                        "This isn't requested by you!", ephemeral=True
                    )
                else:
                    await interaction.response.defer()
                    input = interaction.values[0]
                    cogs = self.bot.get_cog(input.capitalize())
                    embed = disnake.Embed(
                        title=f"\{CogEmoji[cogs.qualified_name]} {cogs.qualified_name}",
                        description="Commands belonging this module -",
                        color=14667786,
                    )
                    embed.set_author(
                        name=self.bot.user.display_name,
                        icon_url=self.bot.user.avatar.url,
                    )
                    embed.set_footer(
                        text=f"Requested by {ctx.author.display_name}",
                        icon_url=ctx.author.display_avatar.url,
                    )

                    if cogs.qualified_name == "Nsfw":
                        if not ctx.channel.is_nsfw():
                            embed.add_field(
                                name="NSFW Module",
                                value="Only available in NSFW channels.",
                            )
                        else:
                            for command in cogs.get_commands():
                                if not command.hidden:
                                    embed.add_field(
                                        name=f"**{command.name}**",
                                        value=f"DESCRIPTION - {command.description}",
                                        inline=False,
                                    )
                    else:
                        for command in cogs.get_slash_commands():
                            embed.add_field(
                                name=f"**{command.name}**",
                                value=f"DESCRIPTION - {command.description}",
                                inline=False,
                            )
                    await ctx.edit_original_message(embed=embed)

            async def on_timeout(self=view):
                for button in self.children:
                    button.disabled = True
                await ctx.edit_original_message(view=view)

            menu.callback = callback
            view.timeout = 15
            view.on_timeout = on_timeout
            await ctx.send(embed=embed, view=view)
        else:
            if input.capitalize() in self.bot.cogs:
                cogs = self.bot.get_cog(input.capitalize())
                embed = disnake.Embed(
                    title=f"\{CogEmoji[cogs.qualified_name]} {cogs.qualified_name}",
                    description="Commands belonging this module -",
                    color=14667786,
                )
                embed.set_author(
                    name=self.bot.user.display_name, icon_url=self.bot.user.avatar.url
                )
                embed.set_footer(
                    text=f"Requested by {ctx.author.display_name}",
                    icon_url=ctx.author.display_avatar.url,
                )
                if cogs.qualified_name == "Nsfw":
                    if not ctx.channel.is_nsfw():
                        raise NSFWChannel("Only available in NSFW channels.")
                else:
                    for command in cogs.get_slash_commands():
                        embed.add_field(
                            name=f"**/{command.body.name}**",
                            value=f"DESCRIPTION - {command.body.description}",
                            inline=False,
                        )
                await ctx.send(embed=embed)
            elif any(
                input.lower() == command.name for command in self.bot.slash_commands
            ):
                for command in self.bot.slash_commands:
                    if command.name == input.lower():
                        try:
                            embed = disnake.Embed(title="Command Help", color=14667786)
                            embed.set_author(
                                name=self.bot.user.display_name,
                                icon_url=self.bot.user.avatar.url,
                            )
                            embed.set_footer(
                                text=f"Requested by {ctx.author.display_name}",
                                icon_url=ctx.author.display_avatar.url,
                            )
                            for cmd in (command.all_commands).values():
                                embed.add_field(
                                    name=cmd.qualified_name, value=cmd.description
                                )
                        except AttributeError:
                            embed = disnake.Embed(
                                title="Command Help",
                                description=command.description,
                                color=14667786,
                            )
                            embed.set_author(
                                name=self.bot.user.display_name,
                                icon_url=self.bot.user.avatar.url,
                            )
                            embed.set_footer(
                                text=f"Requested by {ctx.author.display_name}",
                                icon_url=ctx.author.display_avatar.url,
                            )
                        await ctx.send(embed=embed)
            else:
                embed = disnake.Embed(
                    description=f"I've never heard from a module/command called `{input}` before",
                    color=14667786,
                )
                await ctx.send(embed=embed, delete_after=4)

    @commands.guild_only()
    @commands.slash_command(
        name="about", description="Shows information about the bot."
    )
    async def about(self, interaction: disnake.ApplicationCommandInteraction):
        await interaction.response.defer()
        owner = await self.bot.fetch_user(746287255521460226)
        t_members = []
        for guild in self.bot.guilds:
            for member in guild.members:
                if not member in t_members and not member.bot:
                    t_members.append(member)
        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )
        cmds = 0
        for cmd in self.bot.slash_commands:
            cmds += len(cmd.children)
        cmds += len(self.bot.application_commands)

        sources = ["YouTube", "Spotify (Playlists only)", "YTMusic"]
        version = sys.version_info
        em = disnake.Embed(
            description=f"I am a simple bot made by a school student and I am completely programmed by {owner} alone! Ideas were taken from some of the *good* GITs 🙃. He started with a censor bot for his server and ended up with me in front of you all. Please appreciate my master's efforts by helping him with bugs and your precious feedback!\n\n__**BOT VERSION**__\n`Version 1.0 (STABLE)` - Latest stable available version!\n__**KNOWN BUGS**__\n`info-character` and `info-instagram` commands not working. If you encounter new, join support server.\n__**NEW RELEASE**__\nBug improvements, Temporary VCs and Tagging System. More of a moderator bot!.",
            colour=53759,
            timestamp=dt.datetime.utcnow(),
        )
        em.set_author(
            name=self.bot.user.display_name, icon_url=f"{self.bot.user.avatar.url}"
        )

        em.add_field(
            name="Bot",
            value=f"{self.bot.icons['arrow']} **Servers**: `{len(self.bot.guilds)}`\n{self.bot.icons['arrow']} **Users**: `{len(self.bot.users)}`\n{self.bot.icons['arrow']} **Commands**: `{cmds}`",
            inline=True,
        )

        em.add_field(
            name="Bot Owner",
            value=f"{self.bot.icons['arrow']} **Name**: `{owner}`\n{self.bot.icons['arrow']} **ID**: `{owner.id}`\n{self.bot.icons['arrow']} **Server**: [Devil's Paradise](https://discord.gg/WdnPB5D3cq)",
            inline=True,
        )
        em.add_field(
            name="Song sources I support!", value="\n".join(sources), inline=False
        )

        em.set_thumbnail(url=self.bot.user.avatar.url)
        em.set_footer(
            text=f"Python {version[0]}.{version[1]}.{version[2]} • Disnake {disnake.__version__}",
            icon_url = "https://spng.subpng.com/20180712/jrh/kisspng-professional-python-programmer-computer-programmin-python-logo-download-5b47725bdc5820.2110724115314089879026.jpg"
        )
        await interaction.edit_original_message(
            embed=em,
            view=BotInformationView(
                bot=self.bot, player=player, interaction=interaction
            ),
        )

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        config = {
            "_id": str(guild.id),
            "censor": False,
            "nqn": False,
            "logchannel": "",
            "blacklist": [],
            "whitelist": [],
            "whitechannels": [],
        }
        await self.bot.database.Configs.insert_one(config)

        me = await self.bot.fetch_user(746287255521460226)
        await me.send(f"Joined {guild.name} members = {guild.member_count}")

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        await self.bot.database.Configs.delete_one({"_id": str(guild.id)})
        me = await self.bot.fetch_user(746287255521460226)
        await me.send(f"Left {guild.name} members = {guild.member_count}")

    @commands.Cog.listener()
    async def on_autopost_success(self):
        self.bot.logger.info(
            f"Posted server count ({self.bot.topggpy.guild_count}), shard count ({self.bot.shard_count})"
        )


def setup(bot):
    bot.add_cog(Help(bot))
