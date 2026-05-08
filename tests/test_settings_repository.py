import sqlite3
from pathlib import Path

from discordbot.config import AppConfig
from discordbot.constants import DEFAULT_MAX_RESPONSE_CHARS
from discordbot.storage.settings_repository import SettingsRepository


def test_get_guild_settings_returns_defaults_when_row_is_missing() -> None:
    connection = sqlite3.connect(":memory:")
    connection.execute(
        """
        CREATE TABLE guild_settings (
            guild_id INTEGER PRIMARY KEY,
            is_enabled INTEGER NOT NULL DEFAULT 1,
            allowed_channel_ids TEXT NOT NULL DEFAULT '',
            ollama_model TEXT,
            system_prompt TEXT,
            max_history_messages INTEGER,
            max_response_chars INTEGER,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    repository = SettingsRepository(
        connection=connection,
        config=AppConfig(
            discord_bot_token="token",
            discord_webhook_notify_logs=False,
            discord_webhook_notify_logs_min_level="ERROR",
            discord_webhook_notify_shutdown=True,
            discord_webhook_notify_startup=True,
            discord_webhook_urls=(),
            mention_response="ready",
            default_allowed_channel_ids=(100, 200),
            log_level="INFO",
            max_history_messages=20,
            max_response_chars=DEFAULT_MAX_RESPONSE_CHARS,
            ollama_base_url="http://ollama:11434",
            ollama_model="qwen3:8b",
            ollama_prewarm_enabled=True,
            ollama_prewarm_prompt="warm up",
            ollama_timeout_seconds=60,
            show_steps=False,
            sqlite_path=Path("data/test.db"),
            system_prompt="system prompt",
            vision_enabled=True,
            vision_image_only_prompt="describe image",
            vision_max_pixels=2073600,
            web_search_enabled=False,
            web_search_max_results=3,
            web_search_timeout_seconds=10,
            web_search_country="JP",
            web_search_language="ja",
            brave_search_api_key="",
        ),
    )

    settings = repository.get_guild_settings(123)

    assert settings.guild_id == 123
    assert settings.is_enabled is True
    assert settings.allowed_channel_ids == (100, 200)


def test_get_guild_settings_returns_persisted_values() -> None:
    connection = sqlite3.connect(":memory:")
    connection.execute(
        """
        CREATE TABLE guild_settings (
            guild_id INTEGER PRIMARY KEY,
            is_enabled INTEGER NOT NULL DEFAULT 1,
            allowed_channel_ids TEXT NOT NULL DEFAULT '',
            ollama_model TEXT,
            system_prompt TEXT,
            max_history_messages INTEGER,
            max_response_chars INTEGER,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.execute(
        """
        INSERT INTO guild_settings (guild_id, is_enabled, allowed_channel_ids)
        VALUES (123, 0, '300,400')
        """
    )
    repository = SettingsRepository(
        connection=connection,
        config=AppConfig(
            discord_bot_token="token",
            discord_webhook_notify_logs=False,
            discord_webhook_notify_logs_min_level="ERROR",
            discord_webhook_notify_shutdown=True,
            discord_webhook_notify_startup=True,
            discord_webhook_urls=(),
            mention_response="ready",
            default_allowed_channel_ids=(),
            log_level="INFO",
            max_history_messages=20,
            max_response_chars=DEFAULT_MAX_RESPONSE_CHARS,
            ollama_base_url="http://ollama:11434",
            ollama_model="qwen3:8b",
            ollama_prewarm_enabled=True,
            ollama_prewarm_prompt="warm up",
            ollama_timeout_seconds=60,
            show_steps=False,
            sqlite_path=Path("data/test.db"),
            system_prompt="system prompt",
            vision_enabled=True,
            vision_image_only_prompt="describe image",
            vision_max_pixels=2073600,
            web_search_enabled=False,
            web_search_max_results=3,
            web_search_timeout_seconds=10,
            web_search_country="JP",
            web_search_language="ja",
            brave_search_api_key="",
        ),
    )

    settings = repository.get_guild_settings(123)

    assert settings.guild_id == 123
    assert settings.is_enabled is False
    assert settings.allowed_channel_ids == (300, 400)
