from __future__ import annotations

from typing import TYPE_CHECKING

from discord.ext import commands

if TYPE_CHECKING:
    from distrello.bot import Distrello


class TemplateCog(commands.Cog):
    def __init__(self, bot: Distrello) -> None:
        self.bot = bot


async def setup(bot: Distrello) -> None:
    await bot.add_cog(TemplateCog(bot))
