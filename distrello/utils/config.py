from __future__ import annotations

from typing import Literal

from pydantic_settings import BaseSettings


class Config(BaseSettings):
    db_url: str
    trello_api_key: str
    discord_bot_token: str
    env: Literal["dev", "prod"] = "dev"


CONFIG = Config()  # pyright: ignore[reportCallIssue]
