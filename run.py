from __future__ import annotations

import asyncio
import contextlib

import aiohttp
import discord
from loguru import logger
from sqlmodel import SQLModel

from distrello.api import TrelloOAuthCallbackHandler
from distrello.bot import Distrello
from distrello.db.session import engine
from distrello.utils.config import CONFIG
from distrello.utils.logging import setup_logging
from distrello.utils.misc import wrap_task_factory

discord.VoiceClient.warn_nacl = False


async def create_tables() -> None:
    async with engine.begin() as conn:
        try:
            await conn.run_sync(SQLModel.metadata.create_all)
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
            logger.error("Application will continue, but database functionality may be limited")
        else:
            logger.info("Successfully created database tables")


async def main() -> None:
    wrap_task_factory()
    await create_tables()

    async with aiohttp.ClientSession() as session, Distrello(session) as bot:
        with contextlib.suppress(KeyboardInterrupt, asyncio.CancelledError):
            api = TrelloOAuthCallbackHandler()
            asyncio.create_task(api.run())  # noqa: RUF006

            await bot.start(CONFIG.discord_bot_token)


if __name__ == "__main__":
    setup_logging("logs/bot.log")
    asyncio.run(main())
