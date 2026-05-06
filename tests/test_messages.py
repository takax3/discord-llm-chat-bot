from discordbot.messages import format_message


def test_format_message_returns_thinking_message() -> None:
    assert format_message("thinking") == "Thinking..."


def test_format_message_returns_reply_context_log_message() -> None:
    message = format_message(
        "reply_context_received",
        user_id=1,
        channel_id=2,
        reference_message_id=3,
    )

    assert "reference_message_id=3" in message
