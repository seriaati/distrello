from __future__ import annotations

import trello
from sqlalchemy import BigInteger, ForeignKey, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, Relationship, mapped_column, relationship

from distrello.utils.config import CONFIG


class Base(DeclarativeBase):
    pass


class ServerBoardLink(Base):
    __tablename__ = "server_boards"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    """Discord server ID."""
    api_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    """Trello API token, None if not set yet."""

    board_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    """Trello board ID, None if not set yet."""
    completed_list_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    """Trello list ID for completed cards, None if not set yet."""

    forums: Relationship[list[ForumListLink]] = relationship(
        "DiscordForum", back_populates="server", cascade="all, delete-orphan"
    )

    @property
    def trello(self) -> trello.TrelloAPI:
        if self.api_token is None:
            msg = "Accessing TrelloAPI before API token is set is forbidden."
            raise ValueError(msg)

        return trello.TrelloAPI(api_key=CONFIG.trello_api_key, api_token=self.api_token)


class TagLabelLink(Base):
    __tablename__ = "tag_labels"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    """Discord forum tag ID."""
    label_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    """Trello label ID this tag corresponds to, None if is_completed_tag is True."""
    is_completed_tag: Mapped[bool] = mapped_column(nullable=False, default=False)
    """Whether this tag marks a card as completed."""
    forum_id: Mapped[int] = mapped_column(ForeignKey("discord_forums.id"))
    """Discord forum ID."""

    forum: Relationship[ForumListLink] = relationship("DiscordForum", back_populates="tags")


class ForumListLink(Base):
    __tablename__ = "forum_lists"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    """Discord forum ID."""
    server_id: Mapped[int] = mapped_column(ForeignKey("discord_servers.id"), primary_key=True)
    """Discord server ID."""

    board_id: Mapped[str] = mapped_column(Text, nullable=False)
    """Trello board ID."""
    list_id: Mapped[str] = mapped_column(Text, nullable=False)
    """Trello list ID."""

    server: Relationship[ServerBoardLink] = relationship("DiscordServer", back_populates="forums")
    tags: Relationship[list[TagLabelLink]] = relationship(
        "DiscordForumTag", back_populates="forum", cascade="all, delete-orphan"
    )


class ThreadCardLink(Base):
    __tablename__ = "thread_cards"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    """Discord thread ID."""
    forum_id: Mapped[int] = mapped_column(ForeignKey("discord_forums.id"), primary_key=True)
    """Discord forum ID."""
    card_id: Mapped[str] = mapped_column(Text, nullable=False)
    """Trello card ID."""
