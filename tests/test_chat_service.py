from discordbot.constants import DEFAULT_MAX_RESPONSE_CHARS
from discordbot.domain.guild_settings import GuildSettings
from discordbot.services.chat_service import ChatService, remove_bot_mention


def test_should_respond_when_bot_is_mentioned() -> None:
    service = ChatService(
        mention_response="ready",
        max_response_chars=DEFAULT_MAX_RESPONSE_CHARS,
    )

    should_respond = service.should_respond(
        mentioned_user_ids=[10, 20, 30],
        bot_user_id=20,
        is_reply_to_bot=False,
    )

    assert should_respond is True


def test_should_not_respond_when_bot_is_not_mentioned() -> None:
    service = ChatService(
        mention_response="ready",
        max_response_chars=DEFAULT_MAX_RESPONSE_CHARS,
    )

    should_respond = service.should_respond(
        mentioned_user_ids=[10, 30],
        bot_user_id=20,
        is_reply_to_bot=False,
    )

    assert should_respond is False


def test_should_respond_when_replying_to_bot() -> None:
    service = ChatService(
        mention_response="ready",
        max_response_chars=DEFAULT_MAX_RESPONSE_CHARS,
    )

    should_respond = service.should_respond(
        mentioned_user_ids=[],
        bot_user_id=20,
        is_reply_to_bot=True,
    )

    assert should_respond is True


def test_remove_bot_mention_keeps_user_prompt() -> None:
    normalized = remove_bot_mention("<@12345> hello there", 12345)

    assert normalized == "hello there"


def test_extract_user_message_returns_normalized_message_content() -> None:
    service = ChatService(
        mention_response="ready",
        max_response_chars=DEFAULT_MAX_RESPONSE_CHARS,
    )

    user_message = service.extract_user_message(
        message_content="<@12345> hello there",
        bot_user_id=12345,
    )

    assert user_message == "hello there"


def test_build_empty_message_reply_uses_default_message() -> None:
    service = ChatService(
        mention_response="ready",
        max_response_chars=DEFAULT_MAX_RESPONSE_CHARS,
    )

    reply = service.build_empty_message_reply()

    assert reply == "ready"


def test_build_ollama_error_reply_returns_fallback_message() -> None:
    service = ChatService(
        mention_response="ready",
        max_response_chars=DEFAULT_MAX_RESPONSE_CHARS,
    )

    reply = service.build_ollama_error_reply()

    assert "Ollama" in reply


def test_build_thinking_reply_returns_waiting_message() -> None:
    service = ChatService(
        mention_response="ready",
        max_response_chars=DEFAULT_MAX_RESPONSE_CHARS,
    )

    reply = service.build_thinking_reply()

    assert reply == "Thinking..."


def test_is_guild_message_allowed_returns_true_when_guild_enabled_and_no_channel_limit() -> None:
    service = ChatService(
        mention_response="ready",
        max_response_chars=DEFAULT_MAX_RESPONSE_CHARS,
    )

    is_allowed = service.is_guild_message_allowed(
        guild_settings=GuildSettings(
            guild_id=1,
            is_enabled=True,
            allowed_channel_ids=(),
        ),
        channel_id=10,
    )

    assert is_allowed is True


def test_is_guild_message_allowed_returns_false_when_channel_is_not_allowed() -> None:
    service = ChatService(
        mention_response="ready",
        max_response_chars=DEFAULT_MAX_RESPONSE_CHARS,
    )

    is_allowed = service.is_guild_message_allowed(
        guild_settings=GuildSettings(
            guild_id=1,
            is_enabled=True,
            allowed_channel_ids=(20, 30),
        ),
        channel_id=10,
    )

    assert is_allowed is False


def test_normalize_reply_truncates_long_message() -> None:
    service = ChatService(mention_response="ready", max_response_chars=10)

    reply = service.normalize_reply("123456789012345")

    assert reply == "123456\n..."
