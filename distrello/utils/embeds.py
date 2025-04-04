from __future__ import annotations

import discord


class DefaultEmbed(discord.Embed):
    def __init__(self, *, title: str | None = None, description: str | None = None) -> None:
        super().__init__(title=title, description=description, color=0x5865F2)


class ErrorEmbed(discord.Embed):
    def __init__(self, *, title: str | None = None, description: str | None = None) -> None:
        super().__init__(title=title, description=description, color=0xED4245)
