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
    monkeypatch.setenv("OLLAMA_PREWARM_ENABLED", "false")
    monkeypatch.setenv("OLLAMA_PREWARM_PROMPT", "warm up")
    monkeypatch.setenv("VISION_ENABLED", "false")
    monkeypatch.setenv("VISION_IMAGE_ONLY_PROMPT", "describe image")
    monkeypatch.setenv("VISION_MAX_PIXELS", "1000000")
    monkeypatch.setenv("WEB_SEARCH_ENABLED", "true")
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "brave-key")
    monkeypatch.setenv("WEB_SEARCH_MAX_RESULTS", "3")
    monkeypatch.setenv("WEB_SEARCH_TIMEOUT_SECONDS", "15")
    monkeypatch.setenv("WEB_SEARCH_COUNTRY", "JP")
    monkeypatch.setenv("WEB_SEARCH_LANGUAGE", "jp")
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
    assert config.ollama_prewarm_enabled is False
    assert config.ollama_prewarm_prompt == "warm up"
    assert config.vision_enabled is False
    assert config.vision_image_only_prompt == "describe image"
    assert config.vision_max_pixels == 1000000
    assert config.web_search_enabled is True
    assert config.brave_search_api_key == "brave-key"
    assert config.web_search_max_results == 3
    assert config.web_search_timeout_seconds == 15
    assert config.web_search_country == "JP"
    assert config.web_search_language == "jp"
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


def test_load_config_raises_when_vision_max_pixels_is_not_positive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "token")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "gemma4:26b")
    monkeypatch.setenv("SYSTEM_PROMPT", "system prompt")
    monkeypatch.setenv("VISION_MAX_PIXELS", "0")

    with pytest.raises(ValueError, match="VISION_MAX_PIXELS must be greater than 0."):
        load_config()


def test_load_config_raises_when_brave_key_missing_for_enabled_web_search(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "token")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "gemma4:26b")
    monkeypatch.setenv("SYSTEM_PROMPT", "system prompt")
    monkeypatch.setenv("WEB_SEARCH_ENABLED", "true")
    monkeypatch.delenv("BRAVE_SEARCH_API_KEY", raising=False)

    with pytest.raises(
        ValueError,
        match="BRAVE_SEARCH_API_KEY is required when WEB_SEARCH_ENABLED is true.",
    ):
        load_config()
