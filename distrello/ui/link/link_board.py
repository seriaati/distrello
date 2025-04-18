from __future__ import annotations

import itertools
from typing import TYPE_CHECKING

import discord
from discord import ui

from distrello.errors import AccountNotLinkedError, BotError
from distrello.ui.components import PaginatorView, View
from distrello.utils.embeds import DefaultEmbed

if TYPE_CHECKING:
    from collections.abc import Generator, Sequence

    import trello

    from distrello.utils.types import Interaction


class LinkBoardSelect(ui.Select["LinkBoardView"]):
    def __init__(self, *, boards: Sequence[trello.TrelloBoard], current: str | None) -> None:
        super().__init__(
            placeholder="Select a board to link",
            custom_id="link_board:board_select",
            options=[
                discord.SelectOption(label=board.name, value=board.id, default=current == board.id)
                for board in boards
            ],
            row=4,  # Last row
        )
        self.boards = boards

    async def callback(self, i: Interaction) -> None:
        if i.guild is None:
            return

        selected_board_id = self.values[0]
        selected_board = next(
            (board for board in self.boards if board.id == selected_board_id), None
        )

        if selected_board is None:
            msg = "The selected board is invalid"
            raise BotError(msg)

        server = await i.client.db.get_server(i.guild.id)
        if server is None:
            raise AccountNotLinkedError

        server.board_id = selected_board.id
        await i.client.db.update_server(server)

        embed = DefaultEmbed(
            title="Board Linked",
            description=f"Successfully linked **{i.guild.name}** to **{selected_board.name}**",
        )
        await i.response.edit_message(embed=embed, view=None)


class LinkBoardView(PaginatorView):
    def __init__(self, boards: Sequence[trello.TrelloBoard], current: str | None) -> None:
        self.boards = boards
        self.current = current

        super().__init__(list(self._get_embeds(boards)))
        self._add_board_select()

    @property
    def current_board(self) -> trello.TrelloBoard | None:
        if self.current is None:
            return None
        return next((board for board in self.boards if board.id == self.current), None)

    def _get_embeds(
        self, boards: Sequence[trello.TrelloBoard]
    ) -> Generator[DefaultEmbed, None, None]:
        batched_boards = itertools.batched(boards, 10)
        for page, batch in enumerate(batched_boards, start=1):
            description = "\n".join(f"* [{board.name}]({board.url})" for board in batch)
            embed = DefaultEmbed(
                title=f"Link Discord Server to Trello Board (Page {page})", description=description
            )
            embed.set_footer(
                text=f"Currently linked to: {self.current_board.name if self.current_board else 'None'}"
            )
            yield embed

    def _get_board_select(self) -> ui.Select[LinkBoardView]:
        batched_boards = itertools.batched(self.boards, 10)
        boards = list(batched_boards)[self.index]
        return LinkBoardSelect(boards=boards, current=self.current)

    def _add_board_select(self) -> None:
        item = self.get_item("link_board:board_select")
        if item is not None:
            self.remove_item(item)

        select = self._get_board_select()
        self.add_item(select)

    async def _previous(self, i: Interaction) -> None:
        self._add_board_select()
        await super()._previous(i)

    async def _next(self, i: Interaction) -> None:
        self._add_board_select()
        await super()._next(i)


class LinkBoardConfirmView(View):
    def __init__(self, boards: Sequence[trello.TrelloBoard], current: str | None) -> None:
        self.boards = boards
        self.current = current

        super().__init__()

    @ui.button(label="Yes", style=discord.ButtonStyle.success, custom_id="link_board:confirm_yes")
    async def confirm(self, i: Interaction, _: ui.Button) -> None:
        view = LinkBoardView(self.boards, self.current)
        await view.start(i, edit=True)

    @ui.button(label="No", style=discord.ButtonStyle.danger, custom_id="link_board:confirm_no")
    async def cancel(self, i: Interaction, _: ui.Button) -> None:
        await i.response.edit_message(view=None)
