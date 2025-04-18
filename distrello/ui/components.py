from __future__ import annotations

from typing import TYPE_CHECKING, Any

import discord
from discord import ui

if TYPE_CHECKING:
    from collections.abc import Sequence

    from distrello.utils.types import Interaction

NEXT_PAGE = discord.SelectOption(label="Next page", value="next_page", emoji="➡️")
PREV_PAGE = discord.SelectOption(label="Previous page", value="prev_page", emoji="⬅️")


class Modal(ui.Modal):
    def __init__(self, *, title: str) -> None:
        super().__init__(title=title, timeout=600)

    async def on_error(self, i: Interaction, e: Exception) -> None:
        await i.client.respond_to_error(i, e)

    async def on_submit(self, i: Interaction) -> None:
        await i.response.defer()


class View(ui.View):
    def __init__(self, *, timeout: int | None = 600) -> None:
        super().__init__(timeout=timeout)
        self.message: discord.Message | None = None

    async def on_error(self, i: Interaction, e: Exception, _: ui.Item) -> None:
        await i.client.respond_to_error(i, e)

    async def on_timeout(self) -> None:
        if self.message is None:
            return
        await self.message.edit(view=None)

    def get_item(self, custom_id: str) -> ui.Item[View] | None:
        for item in self.children:
            if item.custom_id == custom_id:  # pyright: ignore[reportAttributeAccessIssue]
                return item
        return None


class PaginatorView(View):
    def __init__(self, embeds: Sequence[discord.Embed]) -> None:
        super().__init__()
        self.embeds = embeds
        self.index = 0

    async def _update_embed(self, i: Interaction) -> None:
        await i.response.edit_message(embed=self.embeds[self.index], view=self)

    async def _previous(self, i: Interaction) -> None:
        self.index = (self.index - 1) % len(self.embeds)
        await self._update_embed(i)

    async def _next(self, i: Interaction) -> None:
        self.index = (self.index + 1) % len(self.embeds)
        await self._update_embed(i)

    @ui.button(label="Previous", style=discord.ButtonStyle.blurple, custom_id="paginator:previous")
    async def previous(self, i: Interaction, _: ui.Button) -> None:
        await self._previous(i)

    @ui.button(label="Next", style=discord.ButtonStyle.blurple, custom_id="paginator:next")
    async def next(self, i: Interaction, _: ui.Button) -> None:
        await self._next(i)

    async def start(self, i: Interaction, *, edit: bool = False, ephemeral: bool = False) -> None:
        if edit:
            if i.response.is_done():
                await i.edit_original_response(embed=self.embeds[self.index], view=self)
                return

            await i.response.edit_message(embed=self.embeds[self.index], view=self)
            return

        if i.response.is_done():
            await i.followup.send(embed=self.embeds[self.index], view=self, ephemeral=ephemeral)
            return

        await i.response.send_message(embed=self.embeds[self.index], view=self, ephemeral=ephemeral)


class PaginatorSelect[V: ui.View](ui.Select):
    def __init__(self, options: list[discord.SelectOption], **kwargs: Any) -> None:
        size = 23
        self.split_options = [options[i : i + size] for i in range(0, len(options), size)]
        self.page_index = 0

        self.next_page = NEXT_PAGE
        self.prev_page = PREV_PAGE

        super().__init__(options=self._process_options(), **kwargs)
        self.view: V

    def _process_options(self) -> list[discord.SelectOption]:
        if self.page_index == 0:
            if len(self.split_options) == 1:
                return self.split_options[0]
            return [self.next_page] + self.split_options[0]
        if self.page_index == len(self.split_options) - 1:
            return [self.prev_page] + self.split_options[-1]
        return [self.next_page, self.prev_page] + self.split_options[self.page_index]

    def change_page(self) -> bool:
        if self.values[0] == "next_page":
            self.page_index += 1
            self.options = self._process_options()
            return True

        if self.values[0] == "prev_page":
            self.page_index -= 1
            self.options = self._process_options()
            return True

        return False
