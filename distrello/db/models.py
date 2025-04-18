from __future__ import annotations

import sqlmodel
import trello

from distrello.utils.config import CONFIG


class ServerBoardLink(sqlmodel.SQLModel, table=True):
    """A Discord server is a Trello board."""

    __tablename__: str = "servers"

    id: int = sqlmodel.Field(primary_key=True, sa_type=sqlmodel.BigInteger)
    """Discord server ID."""
    api_token: str | None = None
    """Trello API token, None if not set yet."""

    board_id: str | None = None
    """Trello board ID, None if not set yet."""
    completed_list_id: str | None = None
    """Trello list ID for completed cards, None if not set yet."""

    # Relationships
    forums: list[ForumListLink] = sqlmodel.Relationship(back_populates="server")

    @property
    def trello(self) -> trello.TrelloAPI:
        if self.api_token is None:
            msg = "Accessing TrelloAPI before API token is set is forbidden."
            raise ValueError(msg)

        return trello.TrelloAPI(api_key=CONFIG.trello_api_key, api_token=self.api_token)


class ForumListLink(sqlmodel.SQLModel, table=True):
    """A forum (channel) in Discord is a list in Trello."""

    __tablename__: str = "forums"

    id: int = sqlmodel.Field(primary_key=True, sa_type=sqlmodel.BigInteger)
    """Discord forum ID."""

    board_id: str
    """Trello board ID."""
    list_id: str
    """Trello list ID."""

    # Relationships
    server_id: int = sqlmodel.Field(foreign_key="servers.id")
    server: ServerBoardLink = sqlmodel.Relationship(back_populates="forums")
    tags: list[TagLabelLink] = sqlmodel.Relationship(back_populates="forum")


class TagLabelLink(sqlmodel.SQLModel, table=True):
    """A tag on a thread in Discord is a label on a card in Trello."""

    __tablename__: str = "tags"

    id: int = sqlmodel.Field(primary_key=True, sa_type=sqlmodel.BigInteger)
    """Discord forum tag ID."""
    label_id: str | None = None
    """Trello label ID this tag corresponds to, None if is_completed_tag is True."""
    is_completed_tag: bool = False
    """Whether this tag marks a card as completed."""

    # Relationships
    forum_id: int = sqlmodel.Field(foreign_key="forums.id")
    forum: ForumListLink = sqlmodel.Relationship(back_populates="tags")


class ThreadCardLink(sqlmodel.SQLModel, table=True):
    """A thread in Discord is a card in Trello."""

    __tablename__: str = "threads"

    id: int = sqlmodel.Field(primary_key=True, sa_type=sqlmodel.BigInteger)
    """Discord thread ID."""
    card_id: str
    """Trello card ID."""

    # Relationships
    forum_id: int = sqlmodel.Field(foreign_key="forums.id")
    forum: ForumListLink = sqlmodel.Relationship(back_populates="threads")
