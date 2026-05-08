from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from discordbot.constants import (
    DEFAULT_LOG_LEVEL,
    DEFAULT_MAX_RESPONSE_CHARS,
    DEFAULT_MENTION_RESPONSE,
    DEFAULT_OLLAMA_PREWARM_ENABLED,
    DEFAULT_OLLAMA_PREWARM_PROMPT,
    DEFAULT_ROUTER_SHOW_STEPS,
    DEFAULT_VISION_ENABLED,
    DEFAULT_VISION_IMAGE_ONLY_PROMPT,
    DEFAULT_VISION_MAX_PIXELS,
    DEFAULT_WEB_SEARCH_COUNTRY,
    DEFAULT_WEB_SEARCH_ENABLED,
    DEFAULT_WEB_SEARCH_LANGUAGE,
    DEFAULT_WEB_SEARCH_MAX_RESULTS,
    DEFAULT_WEB_SEARCH_TIMEOUT_SECONDS,
    DEFAULT_WEBHOOK_MIN_LEVEL_NAME,
    DEFAULT_WEBHOOK_NOTIFY_LOGS,
    DEFAULT_WEBHOOK_NOTIFY_SHUTDOWN,
    DEFAULT_WEBHOOK_NOTIFY_STARTUP,
)


@dataclass(frozen=True)
class AppConfig:
    discord_bot_token: str
    discord_webhook_notify_logs: bool
    discord_webhook_notify_logs_min_level: str
    discord_webhook_notify_shutdown: bool
    discord_webhook_notify_startup: bool
    discord_webhook_urls: tuple[str, ...]
    mention_response: str
    default_allowed_channel_ids: tuple[int, ...]
    log_level: str
    max_history_messages: int
    max_response_chars: int
    ollama_base_url: str
    ollama_model: str
    ollama_router_model: str
    ollama_router_show_steps: bool
    ollama_prewarm_enabled: bool
    ollama_prewarm_prompt: str
    ollama_timeout_seconds: int
    sqlite_path: Path
    system_prompt: str
    vision_enabled: bool
    vision_image_only_prompt: str
    vision_max_pixels: int
    web_search_enabled: bool
    web_search_max_results: int
    web_search_timeout_seconds: int
    web_search_country: str
    web_search_language: str
    brave_search_api_key: str


def _parse_webhook_urls(raw_value: str) -> tuple[str, ...]:
    stripped_value = raw_value.strip()
    if not stripped_value:
        return ()
    urls: list[str] = []
    for part in stripped_value.split(","):
        normalized = part.strip()
        if normalized:
            urls.append(normalized)
    return tuple(urls)


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


def _parse_bool_env(raw_value: str | None, default: bool) -> bool:
    if raw_value is None:
        return default
    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def load_config() -> AppConfig:
    discord_bot_token = os.getenv("DISCORD_BOT_TOKEN", "").strip()
    if not discord_bot_token:
        raise ValueError("DISCORD_BOT_TOKEN is required.")
    discord_webhook_urls = _parse_webhook_urls(os.getenv("DISCORD_WEBHOOK_URL", ""))

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
    ollama_router_model = os.getenv("OLLAMA_ROUTER_MODEL", "").strip() or ollama_model
    ollama_router_show_steps = _parse_bool_env(
        os.getenv("OLLAMA_ROUTER_SHOW_STEPS"),
        DEFAULT_ROUTER_SHOW_STEPS,
    )
    ollama_prewarm_enabled = _parse_bool_env(
        os.getenv("OLLAMA_PREWARM_ENABLED"),
        DEFAULT_OLLAMA_PREWARM_ENABLED,
    )
    ollama_prewarm_prompt = os.getenv(
        "OLLAMA_PREWARM_PROMPT",
        DEFAULT_OLLAMA_PREWARM_PROMPT,
    ).strip()
    if not ollama_prewarm_prompt:
        ollama_prewarm_prompt = DEFAULT_OLLAMA_PREWARM_PROMPT
    system_prompt = os.getenv("SYSTEM_PROMPT", "").strip()
    if not system_prompt:
        raise ValueError("SYSTEM_PROMPT is required.")
    vision_enabled = _parse_bool_env(
        os.getenv("VISION_ENABLED"),
        DEFAULT_VISION_ENABLED,
    )
    vision_image_only_prompt = os.getenv(
        "VISION_IMAGE_ONLY_PROMPT",
        DEFAULT_VISION_IMAGE_ONLY_PROMPT,
    ).strip()
    if not vision_image_only_prompt:
        vision_image_only_prompt = DEFAULT_VISION_IMAGE_ONLY_PROMPT
    vision_max_pixels = int(
        os.getenv("VISION_MAX_PIXELS", str(DEFAULT_VISION_MAX_PIXELS))
    )
    if vision_max_pixels <= 0:
        raise ValueError("VISION_MAX_PIXELS must be greater than 0.")
    web_search_enabled = _parse_bool_env(
        os.getenv("WEB_SEARCH_ENABLED"),
        DEFAULT_WEB_SEARCH_ENABLED,
    )
    web_search_max_results = int(
        os.getenv("WEB_SEARCH_MAX_RESULTS", str(DEFAULT_WEB_SEARCH_MAX_RESULTS))
    )
    if web_search_max_results <= 0:
        raise ValueError("WEB_SEARCH_MAX_RESULTS must be greater than 0.")
    web_search_timeout_seconds = int(
        os.getenv(
            "WEB_SEARCH_TIMEOUT_SECONDS",
            str(DEFAULT_WEB_SEARCH_TIMEOUT_SECONDS),
        )
    )
    if web_search_timeout_seconds <= 0:
        raise ValueError("WEB_SEARCH_TIMEOUT_SECONDS must be greater than 0.")
    web_search_country = os.getenv(
        "WEB_SEARCH_COUNTRY",
        DEFAULT_WEB_SEARCH_COUNTRY,
    ).strip().upper()
    web_search_language = os.getenv(
        "WEB_SEARCH_LANGUAGE",
        DEFAULT_WEB_SEARCH_LANGUAGE,
    ).strip().lower()
    brave_search_api_key = os.getenv("BRAVE_SEARCH_API_KEY", "").strip()
    if web_search_enabled and not brave_search_api_key:
        raise ValueError("BRAVE_SEARCH_API_KEY is required when WEB_SEARCH_ENABLED is true.")
    ollama_timeout_seconds = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "60"))
    sqlite_path = Path(os.getenv("SQLITE_PATH", "./data/discordbot.db")).expanduser()

    return AppConfig(
        discord_bot_token=discord_bot_token,
        discord_webhook_notify_logs=_parse_bool_env(
            os.getenv("DISCORD_WEBHOOK_NOTIFY_LOGS"),
            DEFAULT_WEBHOOK_NOTIFY_LOGS,
        ),
        discord_webhook_notify_logs_min_level=os.getenv(
            "DISCORD_WEBHOOK_NOTIFY_LOGS_MIN_LEVEL",
            DEFAULT_WEBHOOK_MIN_LEVEL_NAME,
        ).upper(),
        discord_webhook_notify_shutdown=_parse_bool_env(
            os.getenv("DISCORD_WEBHOOK_NOTIFY_SHUTDOWN"),
            DEFAULT_WEBHOOK_NOTIFY_SHUTDOWN,
        ),
        discord_webhook_notify_startup=_parse_bool_env(
            os.getenv("DISCORD_WEBHOOK_NOTIFY_STARTUP"),
            DEFAULT_WEBHOOK_NOTIFY_STARTUP,
        ),
        discord_webhook_urls=discord_webhook_urls,
        mention_response=mention_response,
        default_allowed_channel_ids=default_allowed_channel_ids,
        log_level=os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper(),
        max_history_messages=max_history_messages,
        max_response_chars=max_response_chars,
        ollama_base_url=ollama_base_url,
        ollama_model=ollama_model,
        ollama_router_model=ollama_router_model,
        ollama_router_show_steps=ollama_router_show_steps,
        ollama_prewarm_enabled=ollama_prewarm_enabled,
        ollama_prewarm_prompt=ollama_prewarm_prompt,
        ollama_timeout_seconds=ollama_timeout_seconds,
        sqlite_path=sqlite_path,
        system_prompt=system_prompt,
        vision_enabled=vision_enabled,
        vision_image_only_prompt=vision_image_only_prompt,
        vision_max_pixels=vision_max_pixels,
        web_search_enabled=web_search_enabled,
        web_search_max_results=web_search_max_results,
        web_search_timeout_seconds=web_search_timeout_seconds,
        web_search_country=web_search_country,
        web_search_language=web_search_language,
        brave_search_api_key=brave_search_api_key,
    )
