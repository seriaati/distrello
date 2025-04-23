from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

import discord
import trello
from discord import app_commands
from discord.ext import commands
from loguru import logger

from distrello.db.models import ForumListLink
from distrello.errors import AccountNotLinkedError

if TYPE_CHECKING:
    from distrello.bot import Distrello
    from distrello.db.models import ServerBoardLink
    from distrello.utils.types import Interaction


def get_tag_name(tag: discord.ForumTag) -> str:
    """Get the name of a tag, including the unicode emoji if present."""
    if tag.emoji is not None and tag.emoji.is_unicode_emoji():
        return f"{tag.emoji.name} {tag.name}"
    return tag.name


class SyncDiscordToTrello:
    def __init__(self, bot: Distrello, guild: discord.Guild, *, remove_extra: bool) -> None:
        self.bot = bot
        self.guild = guild
        self.remove_extra = remove_extra

    async def _create_label_and_link(
        self, server: ServerBoardLink, forum: ForumListLink, tag: discord.ForumTag
    ) -> None:
        try:
            async with server.trello as api:
                label = await api.create_label(
                    trello.TrelloLabelCreate(
                        name=get_tag_name(tag),
                        color=trello.get_random_label_color(),
                        board_id=forum.board_id,
                    )
                )
        except Exception:
            logger.exception(f"Error creating label for {tag=}")
            return

        await self.bot.db.create_tag(forum_id=forum.id, tag_id=tag.id, label_id=label.id)

    async def _sync_tags(
        self, server: ServerBoardLink, forum: ForumListLink, tags: Sequence[discord.ForumTag]
    ) -> None:
        async with server.trello as api:
            try:
                labels = await api.get_board_labels(forum.board_id)
            except Exception:
                logger.exception(f"Error fetching labels for {forum=}")
                return

        label_map = {label.name: label.id for label in labels}
        tag_names = {get_tag_name(tag) for tag in tags}

        for tag in tags:
            link = await self.bot.db.get_tag(tag.id)
            if link is not None:
                continue

            # Is there an existing label with the same name?
            tag_name = get_tag_name(tag)

            if tag_name in label_map:
                label_id = tag_name
                await self.bot.db.create_tag(forum_id=forum.id, tag_id=tag.id, label_id=label_id)
                logger.debug(f"Created link between {tag.id=} and {label_id=}")
            else:
                # Create a new label and link it to the tag
                await self._create_label_and_link(server, forum, tag)
                logger.debug(f"Created label {tag_name!r} for {tag.id=} and linked them")

        # Remove labels in Trello that are not in Discord
        if not self.remove_extra:
            return

        for label in labels:
            if label.name in tag_names:
                continue

            async with server.trello as api:
                try:
                    await api.delete_label(label.id)
                except Exception:
                    logger.exception(f"Error deleting label {label.id=} from Trello")
                    continue

            await self.bot.db.delete_tag_by_label_id(label.id)
            logger.debug(f"Deleted label {label.id=} and its link from the database")

    async def _sync_threads(
        self, server: ServerBoardLink, forum: ForumListLink, threads: Sequence[discord.Thread]
    ) -> None:
        for thread in threads:
            db_thread = await self.bot.db.get_thread(thread.id)
            db_tags = await self.bot.db.get_tags(forum.id)

            db_tags_map = {tag.id: tag for tag in db_tags}
            tag_label_map = {tag.id: tag.label_id for tag in db_tags if tag.label_id is not None}

            tags = thread.applied_tags

            if db_thread is None:
                message = thread.starter_message or await thread.fetch_message(thread.id)
                description = message.content if message else ""

                try:
                    async with server.trello as api:
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
                        description = message.content if message else ""

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

    async def _sync_forum(self, server: ServerBoardLink, forum: ForumListLink) -> None:
        guild = self.guild

        try:
            channel = guild.get_channel(forum.id) or await guild.fetch_channel(forum.id)
        except (discord.NotFound, discord.Forbidden):
            logger.warning(f"Channel {forum.id} not found in guild {guild.id}")
            return

        if not isinstance(channel, discord.ForumChannel):
            logger.warning(f"Channel {forum.id} is not a forum channel")
            return

        tags = channel.available_tags
        if not tags:
            return

        await self._sync_tags(server, forum, tags)

    async def sync(self) -> None:
        guild = self.guild

        server = await self.bot.db.get_server(guild.id)
        if server is None:
            raise AccountNotLinkedError

        forums = await self.bot.db.get_forums(guild.id)
        for forum in forums:
            await self._sync_forum(server, forum)


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

    async def _sync_discord_to_trello(self, guild: discord.Guild, *, remove: bool) -> None:
        server = await self.bot.db.get_server(guild.id)
        if server is None:
            raise AccountNotLinkedError

        forums = await self.bot.db.get_forums(guild.id)
        for forum in forums:
            try:
                channel = guild.get_channel(forum.id) or await guild.fetch_channel(forum.id)
            except (discord.NotFound, discord.Forbidden):
                logger.warning(f"Channel {forum.id} not found in guild {guild.id}")
                continue

            if not isinstance(channel, discord.ForumChannel):
                logger.warning(f"Channel {forum.id} is not a forum channel")
                continue

            # Sync tags to Trello labels
            tags = channel.available_tags
            if not tags:
                continue

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
