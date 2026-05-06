import sqlite3
from pathlib import Path

from discordbot.config import AppConfig
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
            mention_response="ready",
            default_allowed_channel_ids=(100, 200),
            log_level="INFO",
            sqlite_path=Path("data/test.db"),
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
            mention_response="ready",
            default_allowed_channel_ids=(),
            log_level="INFO",
            sqlite_path=Path("data/test.db"),
        ),
    )

    settings = repository.get_guild_settings(123)

    assert settings.guild_id == 123
    assert settings.is_enabled is False
    assert settings.allowed_channel_ids == (300, 400)
