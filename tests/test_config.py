import pytest

from discordbot.config import load_config
from discordbot.constants import DEFAULT_MENTION_RESPONSE


def test_load_config_raises_when_discord_token_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DISCORD_BOT_TOKEN", raising=False)

    with pytest.raises(ValueError, match="DISCORD_BOT_TOKEN is required."):
        load_config()


def test_load_config_uses_default_mention_response_when_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "token")
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://example.com/webhook")
    monkeypatch.setenv("DISCORD_WEBHOOK_NOTIFY_STARTUP", "false")
    monkeypatch.setenv("DISCORD_WEBHOOK_NOTIFY_SHUTDOWN", "false")
    monkeypatch.setenv("DISCORD_WEBHOOK_NOTIFY_LOGS", "true")
    monkeypatch.setenv("DISCORD_WEBHOOK_NOTIFY_LOGS_MIN_LEVEL", "warning")
    monkeypatch.setenv("DISCORD_MENTION_RESPONSE", "   ")
    monkeypatch.setenv("DEFAULT_ALLOWED_CHANNEL_IDS", "100, 200")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:8b")
    monkeypatch.setenv("SYSTEM_PROMPT", "system prompt")
    monkeypatch.setenv("OLLAMA_TIMEOUT_SECONDS", "90")
    monkeypatch.setenv("MAX_RESPONSE_CHARS", "1500")
    monkeypatch.setenv("SQLITE_PATH", "./data/test.db")
    monkeypatch.setenv("LOG_LEVEL", "debug")

    config = load_config()

    assert config.discord_bot_token == "token"
    assert config.discord_webhook_notify_logs is True
    assert config.discord_webhook_notify_logs_min_level == "WARNING"
    assert config.discord_webhook_notify_shutdown is False
    assert config.discord_webhook_notify_startup is False
    assert config.discord_webhook_url == "https://example.com/webhook"
    assert config.mention_response == DEFAULT_MENTION_RESPONSE
    assert config.default_allowed_channel_ids == (100, 200)
    assert config.log_level == "DEBUG"
    assert config.max_response_chars == 1500
    assert config.ollama_base_url == "http://ollama:11434"
    assert config.ollama_model == "qwen3:8b"
    assert config.system_prompt == "system prompt"
    assert config.ollama_timeout_seconds == 90
    assert config.sqlite_path.name == "test.db"


def test_load_config_raises_when_max_response_chars_is_not_positive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "token")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:8b")
    monkeypatch.setenv("SYSTEM_PROMPT", "system prompt")
    monkeypatch.setenv("MAX_RESPONSE_CHARS", "0")

    with pytest.raises(ValueError, match="MAX_RESPONSE_CHARS must be greater than 0."):
        load_config()
