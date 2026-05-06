from discordbot.messages import format_message


def test_format_message_returns_thinking_message() -> None:
    assert format_message("thinking") == "Thinking..."
