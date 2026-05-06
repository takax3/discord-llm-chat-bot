from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from discordbot.constants import (
    DEFAULT_LOG_LEVEL,
    DEFAULT_MAX_RESPONSE_CHARS,
    DEFAULT_MENTION_RESPONSE,
)


@dataclass(frozen=True)
class AppConfig:
    discord_bot_token: str
    mention_response: str
    default_allowed_channel_ids: tuple[int, ...]
    log_level: str
    max_history_messages: int
    max_response_chars: int
    ollama_base_url: str
    ollama_model: str
    ollama_timeout_seconds: int
    sqlite_path: Path
    system_prompt: str


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
    max_history_messages = int(os.getenv("MAX_HISTORY_MESSAGES", "20"))
    max_response_chars = int(
        os.getenv("MAX_RESPONSE_CHARS", str(DEFAULT_MAX_RESPONSE_CHARS))
    )
    if max_response_chars <= 0:
        raise ValueError("MAX_RESPONSE_CHARS must be greater than 0.")
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434").strip()
    if not ollama_base_url:
        raise ValueError("OLLAMA_BASE_URL is required.")
    ollama_model = os.getenv("OLLAMA_MODEL", "").strip()
    if not ollama_model:
        raise ValueError("OLLAMA_MODEL is required.")
    system_prompt = os.getenv("SYSTEM_PROMPT", "").strip()
    if not system_prompt:
        raise ValueError("SYSTEM_PROMPT is required.")
    ollama_timeout_seconds = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "60"))
    sqlite_path = Path(os.getenv("SQLITE_PATH", "./data/discordbot.db")).expanduser()

    return AppConfig(
        discord_bot_token=discord_bot_token,
        mention_response=mention_response,
        default_allowed_channel_ids=default_allowed_channel_ids,
        log_level=os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper(),
        max_history_messages=max_history_messages,
        max_response_chars=max_response_chars,
        ollama_base_url=ollama_base_url,
        ollama_model=ollama_model,
        ollama_timeout_seconds=ollama_timeout_seconds,
        sqlite_path=sqlite_path,
        system_prompt=system_prompt,
    )
