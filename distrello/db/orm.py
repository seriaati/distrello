from __future__ import annotations

from typing import TYPE_CHECKING

from sqlmodel import select

from distrello.db.models import ForumListLink, ServerBoardLink, TagLabelLink, ThreadCardLink

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession


class Database:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_server(self, server_id: int) -> ServerBoardLink | None:
        stmt = select(ServerBoardLink).where(ServerBoardLink.id == server_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create_server(self, server_id: int) -> ServerBoardLink:
        server = ServerBoardLink(id=server_id)
        self.session.add(server)
        await self.session.commit()
        await self.session.refresh(server)
        return server

    async def update_server(self, server: ServerBoardLink) -> ServerBoardLink:
        await self.session.commit()
        await self.session.refresh(server)
        return server

    async def get_forums(self, server_id: int) -> Sequence[ForumListLink]:
        stmt = select(ForumListLink).where(ForumListLink.server_id == server_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_forum(self, forum_id: int) -> ForumListLink | None:
        stmt = select(ForumListLink).where(ForumListLink.id == forum_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create_forum(
        self, forum_id: int, server_id: int, board_id: str, list_id: str
    ) -> ForumListLink:
        forum = ForumListLink(id=forum_id, server_id=server_id, board_id=board_id, list_id=list_id)
        self.session.add(forum)
        await self.session.commit()
        await self.session.refresh(forum)
        return forum

    async def update_forum(self, forum: ForumListLink) -> ForumListLink:
        await self.session.commit()
        await self.session.refresh(forum)
        return forum

    async def delete_forum(self, forum: ForumListLink) -> None:
        await self.session.delete(forum)
        await self.session.commit()

    async def get_tags(self, forum_id: int) -> Sequence[TagLabelLink]:
        stmt = select(TagLabelLink).where(TagLabelLink.forum_id == forum_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_tag(self, tag_id: int) -> TagLabelLink | None:
        stmt = select(TagLabelLink).where(TagLabelLink.id == tag_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create_tag(self, *, forum_id: int, tag_id: int, label_id: str | None) -> TagLabelLink:
        forum_tag = TagLabelLink(
            id=tag_id, forum_id=forum_id, label_id=label_id, is_completed_tag=label_id is None
        )
        self.session.add(forum_tag)
        await self.session.commit()
        await self.session.refresh(forum_tag)
        return forum_tag

    async def update_tag(self, forum_tag: TagLabelLink) -> TagLabelLink:
        await self.session.commit()
        await self.session.refresh(forum_tag)
        return forum_tag

    async def get_thread(self, thread_id: int) -> ThreadCardLink | None:
        stmt = select(ThreadCardLink).where(ThreadCardLink.id == thread_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create_thread(self, *, thread_id: int, forum_id: int, card_id: str) -> ThreadCardLink:
        forum_thread = ThreadCardLink(id=thread_id, forum_id=forum_id, card_id=card_id)
        self.session.add(forum_thread)
        await self.session.commit()
        await self.session.refresh(forum_thread)
        return forum_thread
