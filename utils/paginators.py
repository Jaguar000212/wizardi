#  -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import textwrap
import typing
from typing import List

import disnake

from utils import menus
from utils.menus import ListPageSource


class ViewPages(disnake.ui.View):
    def __init__(
        self,
        source: menus.PageSource,
        *,
        ctx,
        check_embeds: bool = True,
        compact: bool = False,
    ):
        super().__init__()
        self.source: menus.PageSource = source
        self.check_embeds: bool = check_embeds
        self.ctx = ctx
        self.message: typing.Optional[disnake.Message] = None
        self.current_page: int = 0
        self.compact: bool = compact
        self.input_lock = asyncio.Lock()
        self.clear_items()
        self.fill_items()

    def fill_items(self) -> None:

        if not self.compact:
            self.stop_pages.row = 1

        if self.source.is_paginating():
            max_pages = self.source.get_max_pages()
            use_last_and_first = max_pages is not None and max_pages >= 2
            if use_last_and_first:
                self.add_item(self.go_to_first_page)  # type: ignore
            self.add_item(self.go_to_previous_page)  # type: ignore
            if not self.compact:
                self.add_item(self.go_to_current_page)  # type: ignore
            self.add_item(self.go_to_next_page)  # type: ignore
            if use_last_and_first:
                self.add_item(self.go_to_last_page)  # type: ignore
            self.add_item(self.stop_pages)  # type: ignore

    async def _get_kwargs_from_page(self, page: int) -> typing.Dict[str, typing.Any]:

        value = await disnake.utils.maybe_coroutine(self.source.format_page, self, page)
        if isinstance(value, dict):
            return value
        elif isinstance(value, str):
            return {"content": value, "embed": None}
        elif isinstance(value, disnake.Embed):
            return {"embed": value, "content": None}
        else:
            return {}

    async def show_page(
        self, interaction: disnake.Interaction, page_number: int
    ) -> None:

        page = await self.source.get_page(page_number)
        self.current_page = page_number
        kwargs = await self._get_kwargs_from_page(page)
        self._update_labels(page_number)
        if kwargs:
            if interaction.response.is_done():
                if self.message:
                    await self.message.edit(**kwargs, view=self)
            else:
                await interaction.response.edit_message(**kwargs, view=self)

    def _update_labels(self, page_number: int) -> None:

        self.go_to_first_page.disabled = page_number == 0
        if self.compact:
            max_pages = self.source.get_max_pages()
            self.go_to_last_page.disabled = (
                max_pages is None or (page_number + 1) >= max_pages
            )
            self.go_to_next_page.disabled = (
                max_pages is not None and (page_number + 1) >= max_pages
            )
            self.go_to_previous_page.disabled = page_number == 0
            return

        self.go_to_current_page.label = str(page_number + 1)
        self.go_to_previous_page.label = str(page_number)
        self.go_to_next_page.label = str(page_number + 2)
        self.go_to_next_page.disabled = False
        self.go_to_previous_page.disabled = False
        self.go_to_first_page.disabled = False

        max_pages = self.source.get_max_pages()
        if max_pages is not None:
            self.go_to_last_page.disabled = (page_number + 1) >= max_pages
            if (page_number + 1) >= max_pages:
                self.go_to_next_page.disabled = True
                self.go_to_next_page.label = "…"
            if page_number == 0:
                self.go_to_previous_page.disabled = True
                self.go_to_previous_page.label = "…"

    async def show_checked_page(
        self, interaction: disnake.Interaction, page_number: int
    ) -> None:

        max_pages = self.source.get_max_pages()
        try:
            if max_pages is None:
                # If it doesn't give maximum pages, it cannot be checked
                await self.show_page(interaction, page_number)
            elif max_pages > page_number >= 0:
                await self.show_page(interaction, page_number)
        except IndexError:
            # If an Index Error happens, it has been handled, so it can be ignored.
            pass

    async def interaction_check(self, interaction: disnake.Interaction) -> bool:

        if interaction.user and interaction.user.id in (
            self.ctx.bot.owner_id,
            self.ctx.author.id,
        ):
            return True
        await interaction.response.send_message(
            "This is not your menu.", ephemeral=True
        )
        return False

    async def on_timeout(self) -> None:
        if self.message:
            await self.message.edit(view=None)

    async def on_error(
        self, error: Exception, item: disnake.ui.Item, interaction: disnake.Interaction
    ) -> None:

        safe_send = (
            interaction.response.followup
            if interaction.response.is_done()
            else interaction.response.send_message
        )
        await safe_send(
            "An error occurred while trying to show this page.", ephemeral=True
        )

    async def start(self) -> None:

        if (
            self.check_embeds
            and not self.ctx.channel.permissions_for(self.ctx.me).embed_links
        ):
            await self.ctx.send(
                "Bot does not have embed links permission in this channel."
            )
            return

        await self.source._prepare_once()  # type: ignore
        page = await self.source.get_page(0)
        kwargs = await self._get_kwargs_from_page(page)
        self._update_labels(0)
        self.message = await self.ctx.send(**kwargs, view=self)

    @disnake.ui.button(label="≪", style=disnake.ButtonStyle.grey)
    async def go_to_first_page(
        self, button: disnake.ui.Button, interaction: disnake.Interaction
    ):

        await self.show_page(interaction, 0)

    @disnake.ui.button(label="Back", style=disnake.ButtonStyle.blurple)
    async def go_to_previous_page(
        self, button: disnake.ui.Button, interaction: disnake.Interaction
    ):

        await self.show_checked_page(interaction, self.current_page - 1)

    @disnake.ui.button(label="Current", style=disnake.ButtonStyle.grey, disabled=True)
    async def go_to_current_page(
        self, button: disnake.ui.Button, interaction: disnake.Interaction
    ):
        pass

    @disnake.ui.button(label="Next", style=disnake.ButtonStyle.blurple)
    async def go_to_next_page(
        self, button: disnake.ui.Button, interaction: disnake.Interaction
    ):

        await self.show_checked_page(interaction, self.current_page + 1)

    @disnake.ui.button(label="≫", style=disnake.ButtonStyle.grey)
    async def go_to_last_page(
        self, button: disnake.ui.Button, interaction: disnake.Interaction
    ):

        await self.show_page(interaction, self.source.get_max_pages() - 1)

    @disnake.ui.button(label="Quit", style=disnake.ButtonStyle.red)
    async def stop_pages(self, _: disnake.ui.Button, interaction: disnake.Interaction):

        await interaction.response.defer()
        await interaction.delete_original_message()
        self.stop()


class RichPager(menus.ListPageSource):
    async def format_page(self, menu, entries):
        pages = ""
        for index, entry in enumerate(entries, start=menu.current_page * self.per_page):
            pages = pages + str(entry) + "\n"

        maximum = self.get_max_pages()
        if maximum > 1:
            footer = f"Page {menu.current_page + 1}/{maximum} ({len(self.entries)} entries)"  # type: ignore
            menu.embed.set_footer(text=footer)  # type: ignore

        menu.embed.description = pages  # type: ignore
        return menu.embed  # type: ignore


class EmojiPager(menus.ListPageSource):
    def __init__(self, animated, static, per_page=25):
        super().__init__(entries=(animated + static), per_page=per_page)
        if len(animated) > len(static):
            pages, left_over = divmod(len(animated), per_page)
            if left_over:
                pages += 1

            self._max_pages = pages
        else:
            pages, left_over = divmod(len(static), per_page)
            if left_over:
                pages += 1

            self._max_pages = pages
        self.animated = animated
        self.static = static

    async def format_page(self, menu, entries):
        a = ""
        s = ""
        try:
            for index, emoji in enumerate(
                self.animated[
                    ((menu.current_page) * self.per_page) : (
                        (menu.current_page + 1) * self.per_page
                    )
                ]
            ):
                if (index + 1) % 5 == 0:
                    n = "\n\n"
                else:
                    n = "\t"
                a += str(emoji) + n
        except:
            for index, emoji in enumerate(self.animated[-(self.per_page) : -1]):
                if (index + 1) % 5 == 0:
                    n = "\n\n"
                else:
                    n = "\t"
                a += str(emoji) + n
        try:
            for index, emoji in enumerate(
                self.static[
                    ((menu.current_page) * self.per_page) : (
                        (menu.current_page + 1) * self.per_page
                    )
                ]
            ):
                if (index + 1) % 5 == 0:
                    n = "\n\n"
                else:
                    n = "\t"
                s += str(emoji) + n
        except:
            for index, emoji in enumerate(self.static[-(self.per_page) : -1]):
                if (index + 1) % 5 == 0:
                    n = "\n\n"
                else:
                    n = "\t"
                s += str(emoji) + n
        maximum = self.get_max_pages()
        if maximum > 1:
            footer = f"Page {menu.current_page + 1}/{maximum} ({len(entries)} entries)"  # type: ignore
            menu.embed.set_footer(text=footer)
        # menu.embed.description = " "
        menu.embed.clear_fields()
        menu.embed.add_field(name="Animated Emojis", value=a)
        menu.embed.add_field(name="Static Emojis", value=s)
        for index, field in enumerate(menu.embed.fields):
            if not len(field.value):
                menu.embed.remove_field(index)
        return menu.embed


class LyricPager(menus.ListPageSource):
    async def format_page(self, menu, entries):
        pages = ""
        for index, entry in enumerate(entries, start=menu.current_page * self.per_page):
            pages = pages + str(entry)

        maximum = self.get_max_pages()
        if maximum > 1:
            footer = f"Page {menu.current_page + 1}/{maximum} ({len(self.entries)} entries)"  # type: ignore
            menu.embed.set_footer(text=footer)  # type: ignore

        menu.embed.description = pages  # type: ignore
        return menu.embed  # type: ignore


class EmbedPaginator(disnake.ui.View):
    def __init__(
        self,
        ctx,
        embeds: List[disnake.Embed],
        *,
        timeout: float = 180.0,
        compact: bool = False,
    ):
        super().__init__(timeout=timeout)
        self.message = None
        self.ctx = ctx
        self.input_lock = asyncio.Lock()
        self.embeds = embeds
        self.current_page = 0
        self.compact: bool = compact

    def _update_labels(self, page_number: int) -> None:

        self.go_to_first_page.disabled = page_number == 0
        if self.compact:
            max_pages = len(self.embeds)
            self.go_to_last_page.disabled = (
                max_pages is None or (page_number + 1) >= max_pages
            )
            self.go_to_next_page.disabled = (
                max_pages is not None and (page_number + 1) >= max_pages
            )
            self.go_to_previous_page.disabled = page_number == 0
            return

        self.current_page.label = str(page_number + 1)
        self.go_to_previous_page.label = str(page_number)
        self.go_to_next_page.label = str(page_number + 2)
        self.go_to_next_page.disabled = False
        self.go_to_previous_page.disabled = False
        self.go_to_first_page.disabled = False

        max_pages = len(self.embeds)
        if max_pages is not None:
            self.go_to_last_page.disabled = (page_number + 1) >= max_pages
            if (page_number + 1) >= max_pages:
                self.go_to_next_page.disabled = True
                self.go_to_next_page.label = "…"
            if page_number == 0:
                self.go_to_previous_page.disabled = True
                self.go_to_previous_page.label = "…"

    async def show_checked_page(
        self, interaction: disnake.Interaction, page_number: int
    ) -> None:

        max_pages = len(self.embeds)
        try:
            if max_pages is None:
                # If it doesn't give maximum pages, it cannot be checked
                await self.show_page(interaction)  # type: ignore
            elif max_pages > page_number >= 0:
                await self.show_page(interaction)  # type: ignore
        except IndexError:
            # An error happened that can be handled, so ignore it.
            pass

    async def interaction_check(self, interaction: disnake.Interaction) -> bool:

        if interaction.user and interaction.user.id in (
            self.ctx.bot.owner_id,
            self.ctx.author.id,
        ):
            return True
        await interaction.response.send_message(
            "This pagination menu cannot be controlled by you, sorry!", ephemeral=True
        )
        return False

    async def on_timeout(self) -> None:

        if self.message:
            await self.message.edit(view=None)

    async def show_page(self, page_number: int):

        if (page_number < 0) or (page_number > len(self.embeds) - 1):
            return
        self.current_page = page_number
        embed = self.embeds[page_number]
        embed.set_footer(text=f"Page {self.current_page + 1}/{len(self.embeds)}")
        await self.message.edit(embed=embed)

    @disnake.ui.button(label="≪", style=disnake.ButtonStyle.grey)
    async def go_to_first_page(
        self, button: disnake.ui.Button, interaction: disnake.Interaction
    ):

        await interaction.response.defer()
        await self.show_page(0)

    @disnake.ui.button(label="Back", style=disnake.ButtonStyle.blurple)
    async def go_to_previous_page(
        self, button: disnake.ui.Button, interaction: disnake.Interaction
    ):

        await interaction.response.defer()
        await self.show_page(self.current_page - 1)

    @disnake.ui.button(label="Next", style=disnake.ButtonStyle.blurple)
    async def go_to_next_page(
        self, button: disnake.ui.Button, interaction: disnake.Interaction
    ):

        await interaction.response.defer()
        await self.show_page(self.current_page + 1)

    @disnake.ui.button(label="≫", style=disnake.ButtonStyle.grey)
    async def go_to_last_page(
        self, button: disnake.ui.Button, interaction: disnake.Interaction
    ):

        await interaction.response.defer()
        await self.show_page(len(self.embeds) - 1)

    @disnake.ui.button(label="Quit", style=disnake.ButtonStyle.red)
    async def stop_pages(
        self, button: disnake.ui.Button, interaction: disnake.Interaction
    ):

        await interaction.response.defer()
        await interaction.delete_original_message()
        self.stop()

    async def start(self):

        embed = self.embeds[0]
        embed.set_footer(text=f"Page 1/{len(self.embeds)}")
        self.message = await self.ctx.edit_original_message(embed=embed, view=self)


class SimpleEmbedPages(EmbedPaginator):
    def __init__(self, entries, *, ctx):
        super().__init__(embeds=entries, ctx=ctx)
        self.embed = disnake.Embed(colour=disnake.Colour.blurple())


class Paginator(ListPageSource):
    async def format_page(self, menu, embed: disnake.Embed) -> disnake.Embed:

        if len(menu.source.entries) != 1:  # type: ignore
            em = embed.to_dict()
            if em.get("footer") is not None:
                if em.get("footer").get("text") is not None:
                    if "Page: " not in em.get("footer").get("text"):
                        em["footer"]["text"] = "".join(
                            f"{em['footer']['text']} • Page: {menu.current_page + 1}/{menu.source.get_max_pages()}"  # type: ignore
                            if em["footer"]["text"] is not None
                            else f"Page: {menu.current_page + 1}/{menu.source.get_max_pages()}"  # type: ignore
                        )
                    else:
                        em["footer"]["text"].replace(
                            f"Page: {menu.current_page}/{menu.source.get_max_pages()}",  # type: ignore
                            f"Page: {menu.current_page + 1}/{menu.source.get_max_pages()}",  # type: ignore
                        )
            else:
                em["footer"] = {}  # type: ignore
                em["footer"][
                    "text"
                ] = f"Page: {menu.current_page + 1}/{menu.source.get_max_pages()}"  # type: ignore
            em = disnake.Embed().from_dict(em)
            return em
        return embed


def WrapText(text: str, length: int) -> typing.List[str]:

    wrapper = textwrap.TextWrapper(width=length)
    words = wrapper.wrap(text=text)
    return words


def WrapList(list_: list, length: int) -> typing.List[list]:
    def chunks(seq: list, size: int) -> list:

        for i in range(0, len(seq), size):
            yield seq[i : i + size]

    return list(chunks(list_, length))
