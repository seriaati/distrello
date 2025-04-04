from __future__ import annotations

from typing import TYPE_CHECKING, Any

import discord
import trello
from discord import app_commands
from discord.ext import commands
from loguru import logger

from distrello.errors import AccountNotLinkedError

if TYPE_CHECKING:
    from distrello.bot import Distrello
    from distrello.db.models import ServerBoardLink
    from distrello.utils.types import Interaction


class SyncCog(commands.Cog):
    def __init__(self, bot: Distrello) -> None:
        self.bot = bot

    async def get_thread_card_description(self, thread: discord.Thread) -> str:
        try:
            message = thread.starter_message or await thread.fetch_message(thread.id)
        except discord.NotFound:
            return ""
        else:
            return message.content

    async def get_thread_label_ids(self, forum_id: int) -> list[str]:
        db_tags = await self.bot.db.get_tags(forum_id)
        return [tag.label_id for tag in db_tags if tag.label_id is not None]
    
    async def sync_thread_to_card(self, thread_id: int, guild_id: int, forum_id: int)

    async def sync_forum(
        self, forum_id: int, guild: discord.Guild, server: ServerBoardLink
    ) -> None:
        try:
            channel = guild.get_channel(forum_id) or await guild.fetch_channel(forum_id)
        except (discord.NotFound, discord.Forbidden):
            logger.warning(f"Channel {forum_id} not found in guild {guild.id}")
            return

        if not isinstance(channel, discord.ForumChannel):
            msg = f"Channel {channel.id!r} is not a forum channel"
            raise TypeError(msg)

        forum = await self.bot.db.get_forum(forum_id)
        if forum is None:
            msg = f"Forum {forum_id!r} not found in database"
            raise ValueError(msg)

        tags = channel.available_tags
        if not tags:
            return

        # Sync tags with Trello
        for tag in tags:
            db_tag = await self.bot.db.get_tag(tag.id)
            if db_tag is None:
                try:
                    async with server.trello as api:
                        label = await api.create_label(
                            trello.TrelloLabelCreate(
                                name=tag.name,
                                color=trello.get_random_label_color(),
                                board_id=forum.board_id,
                            )
                        )
                except Exception:
                    logger.exception(f"Error creating label for {tag=}")
                    continue

                db_tag = await self.bot.db.create_tag(
                    forum_id=forum.id, tag_id=tag.id, label_id=label.id
                )

        # Sync threads with Trello
        for thread in channel.threads:
            db_thread = await self.bot.db.get_thread(thread.id)
            db_tags = await self.bot.db.get_tags(forum.id)

            if db_thread is None:
                try:
                    async with server.trello as api:
                        try:
                            message = thread.starter_message or await thread.fetch_message(
                                thread.id
                            )
                        except discord.NotFound:
                            description = ""
                        else:
                            description = message.content

                        label_ids = [tag.label_id for tag in db_tags if tag.label_id is not None]
                        card = await api.create_card(
                            trello.TrelloCardCreate(
                                name=thread.name,
                                description=description,
                                list_id=forum.list_id,
                                label_ids=label_ids,
                            )
                        )
                except Exception:
                    logger.exception(f"Error creating card for {thread=}")
                    continue

                db_thread = await self.bot.db.create_thread(
                    thread_id=thread.id, forum_id=forum.id, card_id=card.id
                )
            else:
                try:
                    async with server.trello as api:
                        message = thread.starter_message or await thread.fetch_message(thread.id)
                        description = message.content

                        await api.update_card(
                            trello.TrelloCardUpdate(
                                id=db_thread.card_id,
                                name=thread.name,
                                description=description,
                                list_id=forum.list_id,
                                label_ids=[
                                    tag.label_id for tag in db_tags if tag.label_id is not None
                                ],
                            )
                        )
                except Exception:
                    logger.exception(f"Error updating card for {thread=}")
                    continue

    async def sync_server(self, server_id: int) -> None:
        server = await self.bot.db.get_server(server_id)
        if server is None:
            raise AccountNotLinkedError

        # Sync all forums in the server
        forums = await self.bot.db.get_forums(server_id)
        for forum in forums:
            try:
                guild = self.bot.get_guild(server_id) or await self.bot.fetch_guild(server_id)
            except discord.HTTPException:
                logger.warning(f"Guild {server_id} not found")
                continue

            await self.sync_forum(forum.id, guild, server)

    @app_commands.command(name="sync", description="Sync the server with Trello")
    async def sync(self, i: Interaction) -> Any:
        if i.guild is None:
            return

        await i.response.defer(ephemeral=True)
        await self.sync_server(i.guild.id)


async def setup(bot: Distrello) -> None:
    await bot.add_cog(SyncCog(bot))
