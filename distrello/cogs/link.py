from __future__ import annotations

from typing import TYPE_CHECKING, Any

import discord
import trello
from discord import app_commands, ui
from discord.ext import commands

from distrello.errors import AccountNotLinkedError, BoardNotLinkedError
from distrello.ui.link.link_board import LinkBoardConfirmView, LinkBoardView
from distrello.ui.link.link_labels import LinkLabelsView
from distrello.ui.link.link_list import LinkListView
from distrello.utils.config import CONFIG
from distrello.utils.embeds import DefaultEmbed, ErrorEmbed

if TYPE_CHECKING:
    from distrello.bot import Distrello
    from distrello.utils.types import Interaction


class LinkCog(commands.GroupCog, name="link"):
    def __init__(self, bot: Distrello) -> None:
        self.bot = bot

    @app_commands.command(name="account", description="Link your Trello account to this server")
    async def link_account(self, i: Interaction) -> Any:
        if i.guild is None:
            return

        await i.response.defer(ephemeral=True)

        url = trello.generate_oauth_url(
            callback_method="fragment",
            return_url=f"{i.client.oauth_redirect_url}?server_id={i.guild.id}",
            scopes=["read", "write"],
            expiration="never",
            key=CONFIG.trello_api_key,
        )

        server = await self.bot.db.get_server(i.guild.id)
        if server is None:
            server = await self.bot.db.create_server(i.guild.id)

        if server.api_token is not None:
            embed = DefaultEmbed(
                title="Already Linked",
                description="This server is already linked to a Trello account.\n"
                "You can still link a new account, but it will replace the current one.\n"
                "This may cause issues with accessing existing boards.",
            )
        else:
            embed = DefaultEmbed(
                title="Link Trello Account",
                description="Click the button below to link your Trello account.",
            )

        view = ui.View(timeout=1)  # Views with only URL buttons don't need to wait for interaction
        view.add_item(ui.Button(label="Authorize", url=url))
        await i.followup.send(embed=embed, view=view)

    @app_commands.command(name="board", description="Link a Trello board to this server")
    async def link_board(self, i: Interaction) -> Any:
        if i.guild is None:
            return

        await i.response.defer(ephemeral=True)

        server = await self.bot.db.get_server(i.guild.id)
        if server is None or server.api_token is None:
            raise AccountNotLinkedError

        async with server.trello as trello:
            boards = await trello.get_boards()

        if not boards:
            embed = ErrorEmbed(
                title="No Boards Found",
                description="You have no boards available to link to this server.",
            )
            await i.followup.send(embed=embed, ephemeral=True)
            return

        if server.board_id is not None:
            board_name = next((board.name for board in boards if board.id == server.board_id), None)
            embed = DefaultEmbed(
                title="Already Linked",
                description=f"This server is already linked to **{board_name or 'an unknown Trello board'}**.\n"
                "You can still link to another board, and it will replace the current one.\n"
                "Do you want to continue?",
            )
            view = LinkBoardConfirmView(boards, server.board_id)
            await i.followup.send(embed=embed, view=view)
            return

        view = LinkBoardView(boards, server.board_id)
        await view.start(i)

    @app_commands.command(name="list", description="Link a Trello list to a forum channel")
    async def link_list(self, i: Interaction, channel: discord.ForumChannel) -> Any:
        if i.guild is None:
            return

        await i.response.defer(ephemeral=True)

        server = await self.bot.db.get_server(i.guild.id)
        if server is None or server.api_token is None:
            raise AccountNotLinkedError

        if server.board_id is None:
            raise BoardNotLinkedError

        async with server.trello as trello:
            lists = await trello.get_board_lists(server.board_id)

        forum = await self.bot.db.get_forum(channel.id)
        current = None if forum is None else forum.list_id

        view = LinkListView(lists, channel.id, current)
        await view.start(i)

    @app_commands.command(
        name="labels", description="Link Trello labels to tags in the forum channel"
    )
    async def link_labels(self, i: Interaction, channel: discord.ForumChannel) -> Any:
        if i.guild is None:
            return

        await i.response.defer(ephemeral=True)

        server = await self.bot.db.get_server(i.guild.id)
        if server is None or server.api_token is None:
            raise AccountNotLinkedError

        if server.board_id is None:
            raise BoardNotLinkedError

        async with server.trello as trello:
            labels = await trello.get_board_labels(server.board_id)

        if not labels:
            embed = ErrorEmbed(
                title="No Labels Found", description="You have no labels in this board."
            )
            await i.followup.send(embed=embed, ephemeral=True)
            return

        tags = channel.available_tags
        if not tags:
            embed = ErrorEmbed(
                title="No Tags Available",
                description="This forum channel has no tags available to link to Trello labels.",
            )
            await i.followup.send(embed=embed, ephemeral=True)
            return

        db_tags = await self.bot.db.get_tags(channel.id)

        view = LinkLabelsView(forum_id=channel.id, labels=labels, tags=tags, db_tags=db_tags)
        await i.followup.send(embed=view.get_embed(), view=view, ephemeral=True)


async def setup(bot: Distrello) -> None:
    await bot.add_cog(LinkCog(bot))
