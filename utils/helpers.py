import asyncio
import datetime
import sys
import time
from motor.motor_asyncio import AsyncIOMotorClient
import disnake
import humanize
from loguru import logger
import json

import wavelink
from utils.paginators import EmojiPager, ViewPages, LyricPager
from wavelink import Player
from os import environ

from disnake.ext.commands import when_mentioned_or

CogEmoji = {
    "Anime": "🎎",
    "Censor": "🤬",
    "Fun": "🎭",
    "Info": "🌐",
    "Moderator": "👮🏻",
    "Music": "🎶",
    "Nsfw": "🔞",
    "Settings": "🛠️",
}


class BotInformation:
    def __init__(
        self,
        bot,
        player: wavelink.Player,
    ):
        self.bot = bot
        self.player = player

    async def get_lavalink_info(
        self, interaction: disnake.ApplicationCommandInteraction
    ) -> disnake.Embed:
        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )
        node: wavelink.Node = player.node

        used = humanize.naturalsize(node.stats.memory_used)
        total = humanize.naturalsize(node.stats.memory_allocated)
        free = humanize.naturalsize(node.stats.memory_free)
        cpu = node.stats.cpu_cores

        fmt = (
            f"**WaveLink:** `{wavelink.__version__}`\n\n"
            f"Connected to `{len(self.bot.wavelink.nodes)}` nodes.\n"
            f"Best available Node `{self.bot.wavelink.get_best_node().__repr__()}`\n"
            f"`{len(self.bot.wavelink.players)}` players are distributed on nodes.\n"
            f"`{node.stats.players}` players are distributed on server.\n"
            f"`{node.stats.playing_players}` players are playing on server.\n\n"
            f"Server Memory: `{used}/{total}` | `({free} free)`\n"
            f"Server CPU: `{cpu}`\n\n"
            f"Server Uptime: `{humanize.precisedelta(datetime.timedelta(milliseconds=node.stats.uptime))}`"
        )
        embed = disnake.Embed(
            description=fmt,
            colour=disnake.Colour.random(),
            title="Lavalink Information",
        ).set_footer(
            text=f"Requested by {interaction.author}",
            icon_url=interaction.author.display_avatar.url,
        )
        return embed

    async def get_bot_info(
        self, interaction: disnake.ApplicationCommandInteraction
    ) -> disnake.Embed:
        version = sys.version_info
        em = disnake.Embed(color=disnake.Colour.random())

        em.add_field(
            name="Bot",
            value=f"{self.bot.icons['arrow']} **Guilds**: `{len(self.bot.guilds)}`\n{self.bot.icons['arrow']} **Users**: `{len(self.bot.users)}`\n{self.bot.icons['arrow']} **Commands**: `{len([cmd for cmd in list(self.bot.walk_commands())if not cmd.hidden])}`",
            inline=True,
        )
        em.add_field(
            name="Bot Owner",
            value=f"{self.bot.icons['arrow']} **Name**: `{self.bot.owner}`\n{self.bot.icons['arrow']} **ID**: `{self.bot.owner.id}`",
            inline=True,
        )
        em.add_field(
            name="Developers",
            value=f"{self.bot.icons['arrow']} `𝙹𝚊𝚐𝚞𝚊𝚛000212#2389`",
            inline=True,
        )
        em.set_thumbnail(url=self.bot.user.display_avatar.url)
        em.set_footer(
            text=f"Python {version[0]}.{version[1]}.{version[2]} • disnake {disnake.__version__}"
        )
        return em

    async def get_uptime(
        self, ctx: disnake.ApplicationCommandInteraction
    ) -> disnake.Embed:
        uptime = disnake.utils.utcnow() - self.bot.start_time
        time_data = humanize.precisedelta(uptime)
        embed = disnake.Embed(
            title="Uptime", description=time_data, colour=disnake.Colour.random()
        ).set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url)
        return embed

    async def get_latency(
        self, ctx: disnake.ApplicationCommandInteraction
    ) -> disnake.Embed:
        times = []
        counter = 0
        embed = disnake.Embed(colour=disnake.Colour.random())
        for _ in range(3):
            counter += 1
            start = time.perf_counter()
            await ctx.edit_original_message(
                content=f"Trying Ping {('.' * counter)} {counter}/3"
            )
            end = time.perf_counter()
            speed = round((end - start) * 1000)
            times.append(speed)
            if speed < 160:
                embed.add_field(
                    name=f"Ping {counter}:",
                    value=f"{self.bot.icons['online']} | {speed}ms",
                    inline=True,
                )
            elif speed > 170:
                embed.add_field(
                    name=f"Ping {counter}:",
                    value=f"{self.bot.icons['away']} | {speed}ms",
                    inline=True,
                )
            else:
                embed.add_field(
                    name=f"Ping {counter}:",
                    value=f"{self.bot.icons['dnd']} | {speed}ms",
                    inline=True,
                )

        embed.add_field(name="Bot Latency", value=f"{round(self.bot.latency * 1000)}ms")
        embed.add_field(
            name="Normal Speed",
            value=f"{round((round(sum(times)) + round(self.bot.latency * 1000)) / 4)}ms",
        )

        embed.set_footer(text=f"Total estimated elapsed time: {round(sum(times))}ms")
        embed.set_author(name=ctx.me.display_name, icon_url=ctx.me.display_avatar.url)
        return embed

    async def get_commands(self, ctx):
        embed = disnake.Embed(colour=disnake.Colour.random())
        embed.set_author(name=ctx.me.display_name, icon_url=ctx.me.display_avatar.url)
        for cog in self.bot.cogs:
            if cog == "Message" or cog == "Help":
                continue
            cogs = self.bot.get_cog(cog)
            cmds = ""
            for command in cogs.get_slash_commands():
                cmds += f"`{command.name}` "

            embed.add_field(name=f"\{CogEmoji[cog]} {cog}", value=cmds, inline=False)

        return embed


class Config:
    def __init__(self):
        with open("./config/config.json", "r") as f:
            self.data = json.load(f)

        with open("./config/icons.json", "r", encoding="utf-8") as r:
            self.emoji = json.load(r)

        self.loop = asyncio.get_event_loop()
        self.client = AsyncIOMotorClient(environ["mongoDB"], io_loop=self.loop)

    async def logChannel(self, ctx):
        return (await self.database.Configs.find_one({"_id": str(ctx.guild.id)}))[
            "logchannel"
        ]

    @property
    def announce(self):
        channel = self.data["bot"]["announcement"]
        return channel

    @property
    def emojis(self):
        return self.emoji

    @property
    def token(self):
        token = environ['token']
        if token is None:
            logger.error("No token found.")
            exit(code=1)
        return token

    @property
    def owner(self):
        owners = self.data["bot"]["owner"]
        if not owners:
            logger.error(
                "No owners found in config, if you are the bot owner, "
                "Please add yourself to the owners list."
            )
            exit(code=1)
        return owners

    @property
    def spotify(self):
        spotify = {
            "clientID":environ['clientID'],
            "clientSecret":environ['clientSecret']
        }
        return spotify

    @property
    def topgg(self):
        return environ["webhookSecret"]

    @property
    def lyricGenius(self):
        return environ["clientToken"]

    @property
    def database(self):
        return self.client.GuildData


class LyricsPaginator(ViewPages):
    def __init__(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        lyrics: str,
        thumbnail: str = None,
    ):
        super().__init__(ctx=ctx, source=LyricPager(lyrics, per_page=3000))
        self.embed = (
            disnake.Embed(
                title="Lyrics",
                colour=disnake.Colour.random(),
            )
            .set_footer(
                text=f"Requested by {ctx.author}",
                icon_url=ctx.author.display_avatar.url,
            )
            .set_thumbnail(url=thumbnail)
        )


class EmojiPaginator(ViewPages):
    def __init__(self, ctx, animated, static):
        super().__init__(ctx=ctx, source=EmojiPager(animated, static))
        self.embed = disnake.Embed(
            title="Available NQN Emojis", colour=disnake.Colour.random()
        ).set_footer(
            text=f"Requested by {ctx.author}",
            icon_url=ctx.author.display_avatar.url,
        )


class BotInformationView(disnake.ui.View):
    def __init__(
        self, interaction: disnake.ApplicationCommandInteraction, bot, player: Player
    ):

        super().__init__(timeout=30)
        self.interaction = interaction
        self.bot = bot
        self.player = player
        self.BotInformation = BotInformation(bot=bot, player=player)
        self.is_message_deleted = False
        self.add_item(
            item=disnake.ui.Button(
                label="Invite",
                url=f"https://discord.com/api/oauth2/authorize?client_id=989801357517135883&permissions=1375299005526&scope=bot%20applications.commands",
                emoji=f"{self.bot.icons['dev']}",
                row=1,
            )
        )
        self.add_item(
            item=disnake.ui.Button(
                label="Support",
                url="https://discord.gg/WdnPB5D3cq",
                emoji=f"{self.bot.icons['discovery']}",
                row=1,
            )
        )

    @disnake.ui.button(
        label="Lavalink", emoji="📜", style=disnake.ButtonStyle.green, row=0
    )
    async def lavalink_info(
        self,
        button: disnake.ui.Button,
        interaction: disnake.ApplicationCommandInteraction,
    ):
        await interaction.response.defer()
        await self.interaction.edit_original_message(
            embed=await self.BotInformation.get_lavalink_info(
                interaction=self.interaction
            )
        )

    @disnake.ui.button(
        label="Latency", emoji="🤖", style=disnake.ButtonStyle.green, row=0
    )
    async def latency(
        self,
        button: disnake.ui.Button,
        interaction: disnake.ApplicationCommandInteraction,
    ):
        try:
            await interaction.response.defer()
        except disnake.errors.NotFound:
            pass
        embed = await self.BotInformation.get_latency(ctx=self.interaction)
        await self.interaction.edit_original_message(embed=embed)

    @disnake.ui.button(
        label="Uptime", emoji="⏳", style=disnake.ButtonStyle.green, row=0
    )
    async def uptime(
        self,
        button: disnake.ui.Button,
        interaction: disnake.ApplicationCommandInteraction,
    ):
        try:
            await interaction.response.defer()
        except disnake.errors.NotFound:
            pass
        await self.interaction.edit_original_message(
            embed=await self.BotInformation.get_uptime(ctx=self.interaction)
        )

    @disnake.ui.button(
        label="Commands", emoji="📃", style=disnake.ButtonStyle.secondary, row=1
    )
    async def Commands(
        self,
        button: disnake.ui.Button,
        interaction: disnake.ApplicationCommandInteraction,
    ):
        try:
            await interaction.response.defer()
        except disnake.errors.NotFound:
            pass
        await self.interaction.edit_original_message(
            embed=await self.BotInformation.get_commands(ctx=self.interaction)
        )

    @disnake.ui.button(
        label="Quit", style=disnake.ButtonStyle.danger, emoji="✖️", row=2
    )
    async def quit(
        self,
        button: disnake.ui.Button,
        interaction: disnake.ApplicationCommandInteraction,
    ):
        try:
            await interaction.response.defer()
        except disnake.errors.NotFound:
            pass
        self.is_message_deleted = True
        await self.interaction.delete_original_message()

    async def on_timeout(self) -> None:
        if self.is_message_deleted:
            return

        for button in self.children:
            button.disabled = True

        try:
            await self.interaction.edit_original_message(view=self)
        except Exception as e:
            logger.error(f"Failed to edit message: {e}")
            return
