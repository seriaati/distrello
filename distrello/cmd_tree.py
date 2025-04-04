from __future__ import annotations

from typing import TYPE_CHECKING

from discord import app_commands

if TYPE_CHECKING:
    from distrello.utils.types import Interaction


class CommandTree(app_commands.CommandTree):
    async def on_error(self, i: Interaction, e: app_commands.AppCommandError) -> None:
        await i.client.respond_to_error(i, e)
