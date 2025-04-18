from __future__ import annotations

from typing import TYPE_CHECKING

from sqlmodel import col, delete, select

from distrello.db.models import ForumListLink, ServerBoardLink, TagLabelLink, ThreadCardLink
from distrello.db.session import get_db

if TYPE_CHECKING:
    from collections.abc import Sequence


class Database:
    async def get_server(self, server_id: int) -> ServerBoardLink | None:
        async with get_db() as session:
            stmt = select(ServerBoardLink).where(ServerBoardLink.id == server_id)
            result = await session.execute(stmt)

        return result.scalars().first()

    async def create_server(self, server_id: int) -> ServerBoardLink:
        async with get_db() as session:
            server = ServerBoardLink(id=server_id)
            session.add(server)
            await session.commit()
            await session.refresh(server)

        return server

    async def update_server(self, server: ServerBoardLink) -> ServerBoardLink:
        async with get_db() as session:
            session.add(server)
            await session.commit()
            await session.refresh(server)

        return server

    async def delete_server(self, server_id: int) -> None:
        async with get_db() as session:
            stmt = delete(ServerBoardLink).where(col(ServerBoardLink.id) == server_id)
            await session.execute(stmt)
            await session.commit()

    async def get_forums(self, server_id: int) -> Sequence[ForumListLink]:
        async with get_db() as session:
            stmt = select(ForumListLink).where(ForumListLink.server_id == server_id)
            result = await session.execute(stmt)

        return result.scalars().all()

    async def get_forum(self, forum_id: int) -> ForumListLink | None:
        async with get_db() as session:
            stmt = select(ForumListLink).where(ForumListLink.id == forum_id)
            result = await session.execute(stmt)

        return result.scalars().first()

    async def create_forum(
        self, forum_id: int, server_id: int, board_id: str, list_id: str
    ) -> ForumListLink:
        async with get_db() as session:
            forum = ForumListLink(
                id=forum_id, server_id=server_id, board_id=board_id, list_id=list_id
            )
            session.add(forum)
            await session.commit()
            await session.refresh(forum)

        return forum

    async def update_forum(self, forum: ForumListLink) -> ForumListLink:
        async with get_db() as session:
            session.add(forum)
            await session.commit()
            await session.refresh(forum)

        return forum

    async def delete_forum(self, forum: ForumListLink) -> None:
        async with get_db() as session:
            session.add(forum)
            await session.delete(forum)
            await session.commit()

    async def get_tags(self, forum_id: int) -> Sequence[TagLabelLink]:
        async with get_db() as session:
            stmt = select(TagLabelLink).where(TagLabelLink.forum_id == forum_id)
            result = await session.execute(stmt)

        return result.scalars().all()

    async def get_tag(self, tag_id: int) -> TagLabelLink | None:
        async with get_db() as session:
            stmt = select(TagLabelLink).where(TagLabelLink.id == tag_id)
            result = await session.execute(stmt)

        return result.scalars().first()

    async def create_tag(self, *, forum_id: int, tag_id: int, label_id: str | None) -> TagLabelLink:
        async with get_db() as session:
            forum_tag = TagLabelLink(
                id=tag_id, forum_id=forum_id, label_id=label_id, is_completed_tag=label_id is None
            )
            session.add(forum_tag)
            await session.commit()
            await session.refresh(forum_tag)

        return forum_tag

    async def update_tag(self, forum_tag: TagLabelLink) -> TagLabelLink:
        async with get_db() as session:
            session.add(forum_tag)
            await session.commit()
            await session.refresh(forum_tag)

        return forum_tag

    async def get_thread(self, thread_id: int) -> ThreadCardLink | None:
        async with get_db() as session:
            stmt = select(ThreadCardLink).where(ThreadCardLink.id == thread_id)
            result = await session.execute(stmt)

        return result.scalars().first()

    async def create_thread(self, *, thread_id: int, forum_id: int, card_id: str) -> ThreadCardLink:
        async with get_db() as session:
            forum_thread = ThreadCardLink(id=thread_id, forum_id=forum_id, card_id=card_id)
            session.add(forum_thread)
            await session.commit()
            await session.refresh(forum_thread)

        return forum_thread
