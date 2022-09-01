#  -*- coding: utf-8 -*-
import asyncio
import datetime
import itertools
import math
import random
import sys
import traceback
import typing

import async_timeout
import disnake
import humanize
from disnake.ui import Item
from loguru import logger
from lyricsgenius import Genius

import wavelink
from bot import Bot
from utils.helpers import LyricsPaginator
from utils.paginators import RichPager, ViewPages


LyricsGenius = Genius(Bot().config.lyricGenius)


class Track(wavelink.Track):

    __slots__ = ("requester",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args)

        self.requester = kwargs.get("requester")


class Queue(asyncio.Queue):
    def __getitem__(self, item):
        if isinstance(item, slice):
            return list(itertools.islice(self._queue, item.start, item.stop, item.step))
        else:
            return self._queue[item]

    def __iter__(self):
        return self._queue.__iter__()

    def __len__(self):
        return self.qsize()

    def count(self):

        return len(self._queue)  # type: ignore

    def __repr__(self):
        return f"<Queue size: {self.qsize()}>"

    def clear(self):

        self._queue.clear()  # type: ignore

    def shuffle(self):

        random.shuffle(self._queue)  # type: ignore

    def remove(self, index: int):

        del self._queue[index]  # type: ignore


class Player(wavelink.Player):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.context: disnake.ApplicationCommandInteraction = kwargs.get("context")
        if self.context:
            self.dj: disnake.Member = self.context.author

        self.queue = Queue()
        self.menu: disnake.Message = None  # type: ignore
        try:
            self.channel = self.context.channel
        except AttributeError:
            pass
        self._loop = False

        self.waiting = False
        self.updating = False
        self.now = None

        self.pause_votes = set()
        self.resume_votes = set()
        self.skip_votes = set()
        self.shuffle_votes = set()
        self.stop_votes = set()
        self.clear_votes = set()

    async def play_next_song(
        self, position: dict = None, play_immediately: bool = False
    ) -> None:

        if position is None:
            position = {"start": 0, "end": 0}
        if self.is_playing or self.waiting:
            return

        self.pause_votes.clear()
        self.resume_votes.clear()
        self.skip_votes.clear()
        self.shuffle_votes.clear()
        self.stop_votes.clear()

        if not self._loop:

            try:
                self.waiting = True
                with async_timeout.timeout(120):
                    track = await self.queue.get()
                    self.now = track
                await self.play(
                    track,
                    start=position["start"],
                    end=position["end"],
                    replace=play_immediately,
                )
                self.waiting = False
                await self.songmenucontroller()
            except asyncio.TimeoutError:
                await self.context.send(
                    embed=disnake.Embed(
                        description=f"Left {(await self.bot.fetch_channel(self.channel_id)).mention} due to inactivity"
                    )
                )
                return await self.teardown()
        else:
            track = self.now
            await self.play(track)
            await self.songmenucontroller()

    async def songmenucontroller(self) -> None:
        if self.updating:
            return

        self.updating = True

        if not self.menu:
            self.menu = await self.channel.send(
                content=None,
                embed=await self.make_song_embed(),
                view=MenuControllerView(
                    player=self, interaction=self.context, bot=self.bot
                ),
            )

        elif not await self.is_menu_available():
            try:
                await self.menu.delete()
            except disnake.HTTPException as e:
                logger.warning(f"Failed to delete menu message: {e}")
            except AttributeError as e:
                logger.warning(f"Failed to delete menu message: {e}")

            await self.channel.send(
                content=None,
                embed=await self.make_song_embed(),
                view=MenuControllerView(self, self.context, bot=self.bot),
            )

        else:
            embed = await self.make_song_embed()
            await self.channel.send(
                content=None,
                embed=embed,
                view=MenuControllerView(self, self.context, bot=self.bot),
            )

        self.updating = False

    async def make_song_embed(self) -> typing.Optional[disnake.Embed]:

        track: Track = self.current
        if not track:
            return None

        channel = self.bot.get_channel(int(self.channel_id))
        position = divmod(self.position, 60000)
        length = divmod(self.now.length, 60000)
        mode = "yes" if self._loop else "off"

        embed = disnake.Embed(
            description=f"Now Playing:\n**`{track.title}`**",
        )
        try:
            embed.set_thumbnail(url=track.thumbnail)
        except disnake.errors.HTTPException:
            pass

        embed.add_field(
            name="Duration",
            value=f"`{humanize.precisedelta(datetime.timedelta(milliseconds=int(track.length)))}`",
        )
        embed.add_field(name="Volume", value=f"**`{self.volume}%`**")
        embed.add_field(
            name="Position",
            value=f"`{int(position[0])}:{round(position[1] / 1000):02}/{int(length[0])}:{round(length[1] / 1000):02}`",
        )
        embed.add_field(name="Track on loop?", value=f"**`{mode}`**")
        embed.add_field(name="Channel", value=f"**`{channel}`**")
        embed.add_field(name="DJ", value=self.dj.mention)
        embed.add_field(name="Video URL", value=f"[Click Here!]({track.uri})")
        embed.add_field(name="Author", value=f"`{track.author}`")
        embed.set_footer(
            text=f"Requested By {track.requester}",
            icon_url=track.requester.display_avatar,
        )
        embed.set_author(
            name=self.bot.user.display_name, icon_url=f"{self.bot.user.avatar.url}"
        )

        return embed

    async def is_menu_available(self) -> bool:

        try:
            async for message in self.context.channel.history(limit=10):
                if message.id == self.menu.message.id:
                    return True
        except (disnake.HTTPException, AttributeError):
            return False

        return False

    async def teardown(self):
        try:
            await self.menu.delete()
        except disnake.HTTPException as e:
            logger.warning(f"Failed to delete menu message: {e}")
        except AttributeError:
            logger.warning("Failed to delete menu message: No menu message")

        try:
            await self.destroy()
        except KeyError as e:
            logger.warning(f"Failed to destroy player: {e}")

    @property
    def loop(self):

        return self._loop

    @loop.setter
    def loop(self, value: bool = False) -> None:

        self._loop = value


class QueuePages(ViewPages):
    def __init__(
        self, entries, ctx: disnake.ApplicationCommandInteraction, per_page: int = 10
    ):
        super().__init__(RichPager(entries, per_page=per_page), ctx=ctx)
        self.embed = disnake.Embed(
            title=f"**{len(entries)}** songs in Queue...",
        ).set_footer(
            text=f"Requested By {ctx.author}", icon_url=ctx.author.display_avatar.url
        )


class MenuControllerView(disnake.ui.View):
    def __init__(
        self,
        player: Player,
        interaction: disnake.ApplicationCommandInteraction,
        bot: Bot,
    ):
        super().__init__(timeout=None)
        self.player = player
        self.interaction = interaction
        self.bot = bot
        self.controller = MenuController(
            self.player, bot=self.bot, interaction=self.interaction
        )

    @disnake.ui.button(label="Pause", style=disnake.ButtonStyle.gray, emoji="⏸️")
    async def pause_song(
        self, button: disnake.Button, interaction: disnake.ApplicationCommandInteraction
    ):

        await self.controller.pause(interaction=interaction)

    @disnake.ui.button(label="Play", style=disnake.ButtonStyle.gray, emoji="▶")
    async def resume_song(
        self, button: disnake.Button, interaction: disnake.ApplicationCommandInteraction
    ):

        await self.controller.resume(interaction=interaction)

    @disnake.ui.button(label="Skip", style=disnake.ButtonStyle.gray, emoji="⏩")
    async def skip_song(
        self, button: disnake.Button, interaction: disnake.ApplicationCommandInteraction
    ):

        await self.controller.skip(interaction=interaction)

    @disnake.ui.button(label="Loop", style=disnake.ButtonStyle.gray, emoji="🔁")
    async def loop_song(
        self, button: disnake.Button, interaction: disnake.ApplicationCommandInteraction
    ):

        await self.controller.loop(interaction=interaction)

    @disnake.ui.button(label="Queue", style=disnake.ButtonStyle.gray, emoji="💺")
    async def show_queue(
        self, button: disnake.Button, interaction: disnake.ApplicationCommandInteraction
    ):
        await self.controller.show_queue(interaction=interaction)

    @disnake.ui.button(label="Lyrics", style=disnake.ButtonStyle.gray, emoji="📃")
    async def show_lyrics(
        self, button: disnake.Button, interaction: disnake.ApplicationCommandInteraction
    ):

        await self.controller.show_lyrics(interaction=interaction)

    @disnake.ui.button(label="Shuffle", style=disnake.ButtonStyle.gray, emoji="🔀")
    async def shuffle_queue(
        self, button: disnake.Button, interaction: disnake.ApplicationCommandInteraction
    ):

        await self.controller.shuffle(interaction=interaction)

    @disnake.ui.button(label="Stop", style=disnake.ButtonStyle.gray, emoji="⏹")
    async def stop_song(
        self, button: disnake.Button, interaction: disnake.ApplicationCommandInteraction
    ):

        await self.controller.stop(interaction=interaction)

    async def on_error(
        self,
        error: Exception,
        item: Item,
        interaction: disnake.MessageInteraction,
    ) -> None:

        if interaction.response.is_done():
            safe_send = interaction.followup.send
        else:
            safe_send = interaction.response.send_message

        await safe_send(
            embed=disnake.Embed(
                description=f"{self.bot.icons['redtick']} An error has occurred while "
                f"executing {interaction.name} command."
                "Try again or contact support."
            )
        )

        print(
            f"Ignoring exception in command {interaction.data.name}: ",
            file=sys.stderr,
        )
        traceback.print_exception(
            type(error), error, error.__traceback__, file=sys.stderr
        )


class MenuController:
    def __init__(
        self,
        player: Player,
        interaction: disnake.ApplicationCommandInteraction,
        bot: Bot,
    ):
        self.player = player
        self.interaction = interaction
        self.bot = bot

    def is_author(self, interaction: disnake.ApplicationCommandInteraction):

        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        return (
            player.dj == interaction.author
            or interaction.author.guild_permissions.administrator
            or interaction.author.guild_permissions.manage_guild
        )  # you can change your
        # permissions here.

    def vote_check(self, interaction: disnake.ApplicationCommandInteraction):

        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )
        channel = self.bot.get_channel(int(player.channel_id))
        required = math.ceil((len(channel.members) - 1) / 2.5)

        if interaction.application_command.name == "stop":
            if len(channel.members) == 3:
                required = 2

        return required

    async def pause(self, interaction: disnake.ApplicationCommandInteraction):

        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        if player.is_paused:
            embed = disnake.Embed(
                description=f"{self.bot.icons['redtick']} `The player is already paused.`"
            )
            return await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )

        if self.is_author(interaction):
            embed = disnake.Embed(
                description=f"{self.bot.icons['info']} `{player.dj}` has paused the player."
            )
            await interaction.response.send_message(
                embed=embed,
                delete_after=5,
            )
            player.pause_votes.clear()

            return await player.set_pause(True)

        required = self.vote_check(interaction)
        player.pause_votes.add(interaction.author)

        if len(player.pause_votes) >= required:
            embed = disnake.Embed(
                description=f"{self.bot.icons['check']} `Vote to pause passed. Pausing player.`"
            )
            await interaction.response.send_message(
                embed=embed,
                delete_after=5,
            )
            player.pause_votes.clear()
            await player.set_pause(True)
        else:
            embed = disnake.Embed(
                description=f"{self.bot.icons['info']} `{interaction.author} has voted to pause the player.`"
            )
            await interaction.response.send_message(
                embed=embed,
                delete_after=5,
            )

    async def resume(self, interaction: disnake.ApplicationCommandInteraction):

        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        if not player.is_connected:
            embed = disnake.Embed(
                description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`"
            )
            return await interaction.response.send_message(
                embed=embed,
                delete_after=5,
            )

        if not player.is_playing:
            embed = disnake.Embed(
                description=f"{self.bot.icons['redtick']} `There is no track playing right now.`"
            )
            return await interaction.response.send_message(
                embed=embed,
                delete_after=5,
            )

        if not player.is_paused:
            embed = disnake.Embed(
                description=f"{self.bot.icons['redtick']} `The player is not paused.`"
            )
            return await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )

        if self.is_author(interaction):
            embed = disnake.Embed(
                description=f"{self.bot.icons['info']} `{player.dj}` has resumed the player."
            )
            await interaction.response.send_message(
                embed=embed,
                delete_after=5,
            )
            player.resume_votes.clear()

            return await player.set_pause(False)

        required = self.vote_check(interaction)
        player.resume_votes.add(interaction.author)

        if len(player.resume_votes) >= required:
            embed = disnake.Embed(
                description=f"{self.bot.icons['check']} `Vote to resume passed. Resuming player.`"
            )
            await interaction.response.send_message(embed=embed, delete_after=5)
            player.resume_votes.clear()
            await player.set_pause(False)
        else:
            embed = disnake.Embed(
                description=f"{self.bot.icons['info']} `{interaction.author} has voted to resume the song.`"
            )
            await interaction.response.send_message(embed=embed, delete_after=5)

    async def skip(self, interaction: disnake.ApplicationCommandInteraction):

        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        if not player.is_connected:
            embed = disnake.Embed(
                description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`"
            )
            return await interaction.response.send_message(
                embed=embed,
                delete_after=5,
            )

        if not player.is_playing:
            embed = disnake.Embed(
                description=f"{self.bot.icons['redtick']} `There is no track playing right now.`"
            )

        if self.is_author(interaction):
            embed = disnake.Embed(
                description=f"{self.bot.icons['info']} `{player.dj}` has skipped the song.",
            )

            await interaction.response.send_message(
                embed=embed,
                delete_after=5,
            )
            player.skip_votes.clear()

            return await player.stop()

        required = self.vote_check(interaction)
        player.skip_votes.add(interaction.author)

        if len(player.skip_votes) >= required:
            embed = disnake.Embed(
                description=f"{self.bot.icons['check']} `Vote to resume passed. Resuming player.`"
            )

            await interaction.response.send_message(embed=embed, delete_after=5)
            player.skip_votes.clear()
            await player.stop()
        else:
            embed = disnake.Embed(
                description=f"{self.bot.icons['info']} `{interaction.author} has voted to resume the song.`"
            )

            await interaction.response.send_message(
                embed=embed,
                delete_after=5,
            )

    async def show_lyrics(self, interaction: disnake.ApplicationCommandInteraction):

        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        name = player.now.title
        await interaction.response.send_message(content="Generating lyrics....")

        lyrics_query = LyricsGenius.search_song(name)
        if not lyrics_query is None:
            if not player.is_playing:
                embed = disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `There is no track playing right now.`",
                )
                return await interaction.edit_original_message(embed=embed)
            else:
                lyrics = lyrics_query.lyrics
                pag = LyricsPaginator(
                    lyrics=lyrics, ctx=interaction, thumbnail=player.current.thumbnail
                )
                await pag.start()
        else:
            return await interaction.edit_original_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `Lyrics for this song is not found.`\nTry using the separate slash command, `/lyrics`.",
                ),
            )

    async def shuffle(self, interaction: disnake.ApplicationCommandInteraction):

        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        if not player.is_connected:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                ),
                delete_after=5,
            )

        if not player.is_playing:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `There is no track playing right now.`",
                )
            )

        if player.is_paused:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `The player is already paused.`",
                ),
                delete_after=5,
            )

        if player.queue.qsize() < 3:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} Add more songs before shuffling.",
                ),
                ephemeral=True,
            )

        if self.is_author(interaction):
            await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} `{player.dj}` has shuffled the queue.",
                ),
                ephemeral=True,
            )

            player.shuffle_votes.clear()
            return player.queue.shuffle()

        required = self.vote_check(interaction)
        player.shuffle_votes.add(interaction.author)

        if len(player.shuffle_votes) >= required:
            await interaction.channel.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} Vote passed, shuffling songs.",
                ),
                delete_after=5,
            )

            player.shuffle_votes.clear()
            player.queue.shuffle()
        else:
            return await interaction.channel.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} `{interaction.author}` has voted to shuffle the queue.",
                )
            )

    async def show_queue(self, interaction: disnake.ApplicationCommandInteraction):

        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        if not player.is_connected:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                ),
                delete_after=5,
            )

        if not player.is_playing:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `There is no track playing right now.`",
                )
            )

        if player.is_paused:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `The player is already paused.`",
                ),
                delete_after=5,
            )

        if player.queue.qsize() == 0:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} There are no more songs "
                    f"in the queue.",
                ),
                ephemeral=True,
            )

        entries = []
        for track in player.queue._queue:
            entries.append(
                f"[{track.title}]({track.uri}) - `{track.author}` - "
                f"`{humanize.precisedelta(datetime.timedelta(milliseconds=track.length))}`"
            )

        await interaction.response.send_message("Loading...")

        paginator = QueuePages(entries=entries, ctx=interaction)

        await paginator.start()

    async def loop(self, interaction: disnake.ApplicationCommandInteraction):

        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )
        if not player.is_connected:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                ),
                delete_after=5,
            )

        if not player.is_playing:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `There is no track playing right now.`",
                )
            )

        if player.is_paused:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `The player is already paused.`",
                ),
                delete_after=5,
            )

        if not self.is_author(interaction):
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} Only the `{player.dj}` can loop this song.",
                ),
                ephemeral=True,
            )

        if player.loop is False:
            await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['check']} Looped the current track.",
                ),
                delete_after=5,
            )
            player.loop = True
            return

        if player.loop is True:
            await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['check']} Unlooped the current track.",
                ),
                delete_after=5,
            )
            player.loop = False
            return

    async def stop(self, interaction: disnake.ApplicationCommandInteraction):
        """
        This method will stop the currently playing song and the music player and only the DJ can use this command.

        Parameters
        ----------
        interaction: disnake.ApplicationCommandInteraction
            The Interaction of the command.
        """
        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )
        if not player.is_connected:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                ),
                delete_after=5,
            )

        if not player.is_playing:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `There is no track playing right now.`",
                )
            )

        if player.is_paused:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `The player is already paused.`",
                ),
                delete_after=5,
            )

        if self.is_author(interaction):
            await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} `{player.dj}` has stopped the player.",
                ),
                delete_after=5,
            )
            return await player.teardown()

        required = self.vote_check(interaction)
        player.stop_votes.add(interaction.author)

        if len(player.stop_votes) >= required:
            await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} Vote passed, stopping the player.",
                ),
                delete_after=5,
            )
            await player.teardown()
        else:
            await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} `{interaction.author}` has voted to stop the song.",
                ),
                delete_after=5,
            )
