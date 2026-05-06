from discordbot.services.chat_service import ChatService, remove_bot_mention


def test_should_respond_when_bot_is_mentioned() -> None:
    service = ChatService(mention_response="ready")

    should_respond = service.should_respond(
        mentioned_user_ids=[10, 20, 30],
        bot_user_id=20,
    )

    assert should_respond is True


def test_should_not_respond_when_bot_is_not_mentioned() -> None:
    service = ChatService(mention_response="ready")

    should_respond = service.should_respond(
        mentioned_user_ids=[10, 30],
        bot_user_id=20,
    )

    assert should_respond is False


def test_remove_bot_mention_keeps_user_prompt() -> None:
    normalized = remove_bot_mention("<@12345> hello there", 12345)

    assert normalized == "hello there"


def test_build_reply_includes_normalized_message_content() -> None:
    service = ChatService(mention_response="ready")

    reply = service.build_reply(
        message_content="<@12345> hello there",
        bot_user_id=12345,
    )

    assert reply == "ready\n\nYou said: hello there"


def test_build_reply_uses_default_message_when_only_mention_is_sent() -> None:
    service = ChatService(mention_response="ready")

    reply = service.build_reply(
        message_content="<@12345>",
        bot_user_id=12345,
    )

    assert reply == "ready"
