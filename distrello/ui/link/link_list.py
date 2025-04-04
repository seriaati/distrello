from __future__ import annotations

import itertools
from typing import TYPE_CHECKING

import discord
from discord import ui

from distrello.errors import AccountNotLinkedError, BoardNotLinkedError, BotError
from distrello.ui.components import PaginatorView
from distrello.utils.embeds import DefaultEmbed

if TYPE_CHECKING:
    from collections.abc import Generator, Sequence

    import trello

    from distrello.utils.types import Interaction


class LinkListSelect(ui.Select["LinkListView"]):
    def __init__(self, *, lists: Sequence[trello.TrelloList], current: str | None) -> None:
        super().__init__(
            placeholder="Select a list to link",
            custom_id="link_list:list_select",
            options=[
                discord.SelectOption(label=list_.name, value=list_.id, default=current == list_.id)
                for list_ in lists
            ],
            row=4,  # Last row
        )
        self.lists = lists

    async def callback(self, i: Interaction) -> None:
        if i.guild is None or self.view is None:
            return

        selected_list_id = self.values[0]
        selected_list = next((list_ for list_ in self.lists if list_.id == selected_list_id), None)

        if selected_list is None:
            msg = "The selected list is invalid"
            raise BotError(msg)

        server = await i.client.db.get_server(i.guild.id)
        if server is None:
            raise AccountNotLinkedError

        if server.board_id is None:
            raise BoardNotLinkedError

        forum = await i.client.db.get_forum(self.view.forum_id)
        if forum is None:
            forum = await i.client.db.create_forum(
                forum_id=self.view.forum_id,
                server_id=i.guild.id,
                board_id=server.board_id,
                list_id=selected_list.id,
            )
        else:
            forum.list_id = selected_list.id
            await i.client.db.update_forum(forum)

        embed = DefaultEmbed(
            title="List Linked",
            description=f"Successfully linked **{selected_list.name}** to <#{self.view.forum_id}>",
        )
        await i.response.edit_message(embed=embed, view=None)


class LinkListView(PaginatorView):
    def __init__(
        self, lists: Sequence[trello.TrelloList], forum_id: int, current: str | None
    ) -> None:
        self.lists = lists
        self.forum_id = forum_id
        self.current = current

        super().__init__(list(self._get_embeds(lists)))
        self._add_list_select()

    @property
    def current_list(self) -> trello.TrelloList | None:
        if self.current is None:
            return None
        return next((list_ for list_ in self.lists if list_.id == self.current), None)

    def _get_embeds(
        self, lists: Sequence[trello.TrelloList]
    ) -> Generator[DefaultEmbed, None, None]:
        batched_lists = itertools.batched(lists, 10)
        for page, batch in enumerate(batched_lists, start=1):
            description = "\n".join(f"* {list_.name}" for list_ in batch)
            embed = DefaultEmbed(
                title=f"Link Discord Forum to Trello List (Page {page})", description=description
            )
            embed.set_footer(
                text=f"Currently linked to: {self.current_list.name if self.current_list else 'None'}"
            )
            yield embed

    def _get_list_select(self) -> ui.Select[LinkListView]:
        batched_lists = itertools.batched(self.lists, 10)
        lists = list(batched_lists)[self.index]
        return LinkListSelect(lists=lists, current=self.current)

    def _add_list_select(self) -> None:
        item = self.get_item("link_list:list_select")
        if item is not None:
            self.remove_item(item)

        select = self._get_list_select()
        self.add_item(select)

    async def _previous(self, i: Interaction) -> None:
        self._add_list_select()
        await super()._previous(i)

    async def _next(self, i: Interaction) -> None:
        self._add_list_select()
        await super()._next(i)
