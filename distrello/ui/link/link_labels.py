from __future__ import annotations

from typing import TYPE_CHECKING, Any

import discord

from distrello.errors import InvalidInputError
from distrello.ui.components import PaginatorSelect, View
from distrello.utils.embeds import DefaultEmbed

if TYPE_CHECKING:
    from collections.abc import Sequence

    import trello

    from distrello.db.models import TagLabelLink
    from distrello.utils.types import Interaction


class LabelSelect(PaginatorSelect["LinkLabelsView"]):
    def __init__(
        self, labels: list[trello.TrelloLabel], tag_id: int, db_tag: TagLabelLink | None
    ) -> None:
        super().__init__(
            placeholder="Select a label to link",
            custom_id="link_label:label_select",
            options=[
                discord.SelectOption(
                    label="Mark card as completed",
                    value="none",
                    default=db_tag is not None and db_tag.label_id is None,
                )
            ]
            + [
                discord.SelectOption(
                    label=f"{label.name or 'Unnamed label'} ({label.color})",
                    value=label.id,
                    default=db_tag is not None and db_tag.label_id == label.id,
                )
                for label in labels
            ],
        )
        self.labels = labels
        self.tag_id = tag_id

    async def callback(self, i: Interaction) -> None:
        changed = self.change_page()
        if changed:
            await i.response.edit_message(view=self.view)
            return

        label = None if self.values[0] == "none" else self.view.get_label(self.values[0])
        db_tag = self.view.get_db_tag(self.tag_id)

        if db_tag is None:
            db_tag = await i.client.db.create_tag(
                forum_id=self.view.forum_id,
                tag_id=self.tag_id,
                label_id=None if label is None else label.id,
            )

        db_tag.label_id = None if label is None else label.id
        await i.client.db.update_tag(db_tag)

        self.view.db_tags = await i.client.db.get_tags(self.view.forum_id)

        embed = self.view.get_embed()
        self.view.remove_item(self)
        self.view.add_item(TagSelect(self.view.tags))
        await i.response.edit_message(embed=embed, view=self.view)


class TagSelect(PaginatorSelect["LinkLabelsView"]):
    def __init__(self, tags: Sequence[discord.ForumTag]) -> None:
        super().__init__(
            placeholder="Select a tag to link",
            custom_id="link_label:tag_select",
            options=[discord.SelectOption(label=tag.name, value=str(tag.id)) for tag in tags],
        )
        self.tags = tags

    async def callback(self, i: Interaction) -> Any:
        changed = self.change_page()
        if changed:
            await i.response.edit_message(view=self.view)
            return

        tag = self.view.get_tag(int(self.values[0]))
        if tag is None:
            msg = "The selected tag is invalid"
            raise InvalidInputError(msg)

        db_tag = self.view.get_db_tag(tag.id)

        self.view.remove_item(self)
        self.view.add_item(LabelSelect(self.view.labels, tag.id, db_tag))
        await i.response.edit_message(view=self.view)


class LinkLabelsView(View):
    def __init__(
        self,
        *,
        forum_id: int,
        labels: list[trello.TrelloLabel],
        tags: Sequence[discord.ForumTag],
        db_tags: Sequence[TagLabelLink],
    ) -> None:
        super().__init__()
        self.forum_id = forum_id
        self.labels = labels
        self.tags = tags
        self.db_tags = db_tags

        self.add_item(TagSelect(tags))

    def get_label(self, label_id: str) -> trello.TrelloLabel | None:
        return next((label for label in self.labels if label.id == label_id), None)

    def get_tag(self, tag_id: int) -> discord.ForumTag | None:
        return next((tag for tag in self.tags if tag.id == tag_id), None)

    def get_db_tag(self, tag_id: int) -> TagLabelLink | None:
        return next((tag for tag in self.db_tags if tag.id == tag_id), None)

    def get_embed(self) -> discord.Embed:
        embed = DefaultEmbed(title="Link Discord Forum Labels to Trello Tags")

        for tag in self.tags:
            db_tag = self.get_db_tag(tag.id)
            if db_tag is None:
                continue

            if db_tag.label_id is None:
                embed.add_field(
                    name=f"{tag.emoji or ''} {tag.name} → ✅",
                    value="Mark card as completed",
                    inline=False,
                )
                continue

            label = self.get_label(db_tag.label_id)
            if label is None:
                continue

            embed.add_field(
                name=f"{tag.emoji or ''} {tag.name} → {label.name or 'Unnamed label'}",
                value=f"Color: {label.color}",
                inline=False,
            )

        return embed
