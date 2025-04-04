from __future__ import annotations

import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

import discord
from discord.ext import commands
from loguru import logger

from distrello.cmd_tree import CommandTree
from distrello.db.orm import Database
from distrello.errors import BotError
from distrello.utils.config import CONFIG
from distrello.utils.embeds import ErrorEmbed

if TYPE_CHECKING:
    import aiohttp
    from sqlalchemy.ext.asyncio import AsyncSession

    from distrello.utils.types import Interaction


class Distrello(commands.Bot):
    def __init__(self, session: aiohttp.ClientSession, db_session: AsyncSession) -> None:
        super().__init__(
            commands.when_mentioned,
            intents=discord.Intents.default(),
            allowed_contexts=discord.app_commands.AppCommandContext(
                guild=True, dm_channel=False, private_channel=False
            ),
            tree_cls=CommandTree,
        )
        self.session = session
        self.db = Database(db_session)

    @property
    def oauth_redirect_url(self) -> str:
        if CONFIG.env == "dev":
            return "http://localhost:6721/callback"
        return "https://distrello.seria.moe/callback"

    async def _load_cogs(self) -> None:
        for cog in Path("distrello/cogs").rglob("*.py"):
            try:
                await self.load_extension(".".join(cog.with_suffix("").parts))
            except Exception:
                logger.exception(f"Failed to load cog {cog.stem!r}")
            else:
                logger.info(f"Loaded cog {cog.stem!r}")

        await self.load_extension("jishaku")

    @staticmethod
    def get_error_embed(e: Exception) -> ErrorEmbed:
        if isinstance(e, discord.app_commands.CommandInvokeError | commands.CommandInvokeError):
            e = e.original

        if isinstance(e, BotError):
            return e.embed

        code = uuid.uuid4().hex[:8]
        now = discord.utils.utcnow()
        logger.exception(f"An unknown error occurred, code={code}")
        return ErrorEmbed(
            title="An unknown error occurred, please contact the developer",
            description=f"Error code: {code}\nNow: {now}\nError message: `{e}`",
        )

    async def respond_to_error(self, i: Interaction, e: Exception) -> Any:
        embed = self.get_error_embed(e)
        if i.response.is_done():
            await i.followup.send(embed=embed, ephemeral=True)
            return
        await i.response.send_message(embed=embed, ephemeral=True)

    async def setup_hook(self) -> None:
        await self._load_cogs()
