from __future__ import annotations

from distrello.utils.embeds import ErrorEmbed


class BotError(Exception):
    def __init__(self, title: str, description: str | None = None) -> None:
        self._title = title
        self._description = description

    @property
    def embed(self) -> ErrorEmbed:
        return ErrorEmbed(title=self._title, description=self._description)


class AccountNotLinkedError(BotError):
    def __init__(self) -> None:
        super().__init__(
            title="Account not Linked",
            description="This server is not linked to a Trello account, use `/link account` to link it.",
        )


class BoardNotLinkedError(BotError):
    def __init__(self) -> None:
        super().__init__(
            title="Board not Linked",
            description="This server is not linked to a Trello board, use `/link board` to link it.",
        )


class InvalidInputError(BotError):
    def __init__(self, detail: str) -> None:
        super().__init__(title="Invalid Input", description=detail)
