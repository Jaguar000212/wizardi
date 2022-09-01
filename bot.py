import pkgutil
import sys
import traceback
from utils.embed import Embed, logEmbed
from utils.exceptions import NSFWChannel, NoNeko
from utils.helpers import Config
from utils.mongoDB import BotDB
# from utils.keep_alive import keep_alive

from utils.exceptions import NoChannelProvided
from wavelink.errors import NoPermissions, ZeroConnectedNodes

import disnake
from disnake import AllowedMentions, Intents
from disnake.ext import commands
from disnake.ext.commands import errors
from loguru import logger
from utils.CensorBot import CensorBot
from utils.checks import NoVote

import os


config = Config()
intents = Intents.default()
intents.members = True
intents.message_content = True


class Bot(commands.AutoShardedBot):
    def __init__(self, *args, **kwargs):

        super().__init__(
            command_prefix=commands.when_mentioned,
            strip_after_prefix=True,
            allowed_mentions=AllowedMentions(everyone=False, users=True, roles=False),
            intents=intents,
            sync_commands=True,
            owner_id=config.owner,
            reload=True,
            *args,
            **kwargs,
        )
        self.config = config
        self.icons = self.config.emojis
        self.logger = logger
        self.start_time = disnake.utils.utcnow()
        self.database = self.config.database
        self.BotDB = BotDB(bot=self)
        self.censorBot = CensorBot(bot=self)
        self.Embed = Embed
        self.logging = logEmbed
        self.announce = self.config.announce
        # self.alive = keep_alive()
        self.add_check(
            commands.bot_has_permissions(
                read_messages=True,
                send_messages=True,
                embed_links=True,
                read_message_history=True,
                external_emojis=True,
                add_reactions=True,
            ).predicate
        )

    def load_cogs(self, exts) -> None:
        print("|-----------LOADING COGS---------|")
        for m in pkgutil.iter_modules([exts]):
            module = f"cogs.{m.name}"
            try:
                self.load_extension(module)
                print(f"|  Loaded '{m.name}'")
            except Exception as e:
                traceback.print_exception(type(e), e, e.__traceback__, file=sys.stderr)
        print("|--------------------------------|")

    async def on_connect(self):
        print(
            f"|----------Bot Connected---------|\n"
            f"|  Bot name: {self.user.name}\n"
            f"|  Bot ID: {self.user.id}\n"
            f"|  Total Guilds: {len(self.guilds)}\n"
            f"|--------------------------------|"
        )

    async def on_shard_connect(self, shard_id: int):
        activity = disnake.Activity(
            name="Enchantment",
            details=f"wiz help | Shard - {shard_id}",
            url="https://discord.gg/WdnPB5D3cq",
            assets={"large_image": "large_image", "large_image_text": "Wizardi"},
            type=disnake.ActivityType.listening,
        )
        await self.change_presence(
            activity=activity, status=disnake.Status.online, shard_id=shard_id
        )
        print(
            f"|--------Shard Connected---------|\n"
            f"|  Bot name: {self.user.name}\n"
            f"|  Shard ID: {shard_id}\n"
            f"|  Latency: {round(self.get_shard(shard_id).latency * 1000)}ms\n"
            f"|--------------------------------|"
        )

    async def on_ready(self):
        # await self.launch_shards()
        channel = self.get_channel(self.announce)
        await channel.send(
            embed=disnake.Embed(
                description=f"""
```|----------Bot Ready-------------|
|  Bot name: {self.user.name}
|  Bot ID: {self.user.id}
|  Total Guilds: {len(self.guilds)}
|--------------------------------|```
        """
            )
        )

    async def on_shard_ready(self, shard_id: int):
        channel = self.get_channel(self.announce)
        await channel.send(
            embed=disnake.Embed(
                description=f"""
```|-------Shard Initialised--------|
|  Bot name: {self.user.name}
|  Shard ID: {shard_id}
|  Latency: {round(self.get_shard(shard_id).latency * 1000)}ms
|--------------------------------|```
        """
            )
        )

    async def on_resumed(self):
        channel = self.get_channel(self.announce)
        await channel.send(
            embed=disnake.Embed(
                description=f"""
```|----------Bot Resumed-----------|
|  Bot name: {self.user.name}
|  Bot ID: {self.user.id}
|  Total Guilds: {len(self.guilds)}
|--------------------------------|```
        """
            )
        )

    async def on_shard_disconnect(self, shard_id: int):
        channel = self.get_channel(self.announce)
        await channel.send(
            embed=disnake.Embed(
                description=f"""
```|-------Shard Disconnected-------|
|  Bot name: {self.user.name}
|  Shard ID: {shard_id}
|--------------------------------|```
        """
            )
        )

    async def on_slash_command_error(self, ctx: disnake.AppCmdInter, error: Exception):
        ctx.application_command.reset_cooldown(ctx)
        if isinstance(error, errors.BotMissingPermissions):
            await ctx.send(
                embed=disnake.Embed(description=f"`{error}`"), delete_after=4
            )
        elif isinstance(error, NSFWChannel):
            await ctx.send(
                embed=disnake.Embed(description=f"`{error}`"), delete_after=4
            )
        elif isinstance(error, errors.MissingPermissions):
            await ctx.send(
                embed=disnake.Embed(description=f"`{error}`"), delete_after=4
            )
        elif isinstance(error, errors.ChannelNotReadable):
            await ctx.author.send(
                embed=disnake.Embed(
                    description="`No permissions to read channel's content`"
                ),
                delete_after=4,
            )
        elif isinstance(error, errors.BadArgument):
            await ctx.send(
                embed=disnake.Embed(description=f"`{error}`"), delete_after=4
            )
        elif isinstance(error, NoVote):
            view = disnake.ui.View()
            link = disnake.ui.Button(
                label="Vote",
                style=disnake.ButtonStyle.url,
                url="https://top.gg/bot/884117357327429704/vote",
            )
            view.add_item(link)
            embed = disnake.Embed(
                title="Exclusive Command",
                description="This command is exclusively for voters...\nClick to vote!",
                colour=1199267,
            )
            embed.set_author(
                name=self.user.display_name, icon_url=f"{self.user.avatar.url}"
            )
            embed.set_footer(
                text=f"Requested by {ctx.author.display_name}",
                icon_url=ctx.author.display_avatar.url,
            )
            await ctx.send(embed=embed, view=view)
        elif isinstance(error, errors.CommandOnCooldown):
            await ctx.send(
                embed=disnake.Embed(
                    description=f"`This command is on cooldown, try again after {round(error.retry_after)} seconds`"
                ),
                delete_after=4,
            )

        elif isinstance(error, ZeroConnectedNodes):
            return await ctx.send(
                embed=disnake.Embed(
                    description=f"{self.icons['redtick']} `There are no nodes connected.`",
                ),
                delete_after=4,
            )

        elif isinstance(error, NoChannelProvided):
            return await ctx.send(
                embed=disnake.Embed(
                    description=f"{self.icons['redtick']} `You must be connected to a voice channel.`",
                ),
                delete_after=4,
            )

        elif isinstance(error, NoPermissions):
            return await ctx.send(
                embed=disnake.Embed(
                    description=f"{self.icons['redtick']} `{error}`",
                ),
                delete_after=4,
            )

        elif isinstance(error, errors.NoPrivateMessage):
            return await ctx.send(
                embed=disnake.Embed(
                    description=f"{self.icons['redtick']} `{error}`",
                ),
                delete_after=4,
            )
        elif isinstance(error, NoNeko):
            return await ctx.send(
                embed=disnake.Embed(
                    description=f"{self.icons['redtick']} `{error}`",
                ),
                delete_after=4,
            )

        elif isinstance(error, errors.CommandInvokeError):
            if type(error.__cause__) == disnake.errors.Forbidden:
                await ctx.send(
                    embed=disnake.Embed(
                        description="`My role's hierarchy and/or permissions don't allow me to do so.`"
                    ),
                    delete_after=4,
                )

            elif type(error.__cause__) == disnake.errors.NotFound:
                pass

            elif type(error.__cause__) == disnake.errors.HTTPException:
                print("Bot has been temporarily banned by Discord")
                os.system("kill 1")
                print("Trying fix...")
                try:
                    self.run(config.token)
                except disnake.errors.HTTPException as e:
                    print("Failed, temporarily banned!")

            else:
                await ctx.send(
                    embed=disnake.Embed(
                        description="`An unknown error occured and the same has been reported to the team.`"
                    ),
                    delete_after=4,
                )
                print(
                    f"Ignoring exception in command {ctx.application_command.name}: ",
                    file=sys.stderr,
                )
                traceback.print_exception(
                    type(error), error, error.__traceback__, file=sys.stderr
                )
                owner = await self.fetch_user(746287255521460226)
                await owner.send(
                    f"Ignoring exception in command {ctx.application_command.name}:\n{type(error.__cause__)}"
                )
        else:
            await ctx.send(
                embed=disnake.Embed(
                    description="`An unknown error occured and the same has been reported to the team.`"
                ),
                delete_after=4,
            )
            print(
                f"Ignoring exception in command {ctx.application_command.name}: ",
                file=sys.stderr,
            )
            traceback.print_exception(
                type(error), error, error.__traceback__, file=sys.stderr
            )
            owner = await self.fetch_user(746287255521460226)
            await owner.send(
                f"Ignoring exception in command {ctx.application_command.name}:\n{error}\n{type(error)}\n{error.__traceback__.tb_frame.f_trace}"
            )
