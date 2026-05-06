from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from discordbot.constants import DEFAULT_LOG_LEVEL, DEFAULT_MENTION_RESPONSE


@dataclass(frozen=True)
class AppConfig:
    discord_bot_token: str
    mention_response: str
    default_allowed_channel_ids: tuple[int, ...]
    log_level: str
    sqlite_path: Path


def _parse_channel_ids(raw_value: str) -> tuple[int, ...]:
    stripped_value = raw_value.strip()
    if not stripped_value:
        return ()

    channel_ids: list[int] = []
    for part in stripped_value.split(","):
        normalized = part.strip()
        if not normalized:
            continue
        channel_ids.append(int(normalized))
    return tuple(channel_ids)


def load_config() -> AppConfig:
    discord_bot_token = os.getenv("DISCORD_BOT_TOKEN", "").strip()
    if not discord_bot_token:
        raise ValueError("DISCORD_BOT_TOKEN is required.")

    mention_response = os.getenv(
        "DISCORD_MENTION_RESPONSE",
        DEFAULT_MENTION_RESPONSE,
    ).strip()
    if not mention_response:
        mention_response = DEFAULT_MENTION_RESPONSE

    default_allowed_channel_ids = _parse_channel_ids(
        os.getenv("DEFAULT_ALLOWED_CHANNEL_IDS", "")
    )
    sqlite_path = Path(os.getenv("SQLITE_PATH", "./data/discordbot.db")).expanduser()

    return AppConfig(
        discord_bot_token=discord_bot_token,
        mention_response=mention_response,
        default_allowed_channel_ids=default_allowed_channel_ids,
        log_level=os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper(),
        sqlite_path=sqlite_path,
    )
