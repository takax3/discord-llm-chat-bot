import pytest

from discordbot.config import load_config
from discordbot.constants import DEFAULT_MENTION_RESPONSE


def test_load_config_raises_when_discord_token_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DISCORD_BOT_TOKEN", raising=False)

    with pytest.raises(ValueError, match="DISCORD_BOT_TOKEN is required."):
        load_config()


def test_load_config_uses_default_mention_response_when_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "token")
    monkeypatch.setenv("DISCORD_MENTION_RESPONSE", "   ")
    monkeypatch.setenv("DEFAULT_ALLOWED_CHANNEL_IDS", "100, 200")
    monkeypatch.setenv("SQLITE_PATH", "./data/test.db")
    monkeypatch.setenv("LOG_LEVEL", "debug")

    config = load_config()

    assert config.discord_bot_token == "token"
    assert config.mention_response == DEFAULT_MENTION_RESPONSE
    assert config.default_allowed_channel_ids == (100, 200)
    assert config.log_level == "DEBUG"
    assert config.sqlite_path.name == "test.db"
