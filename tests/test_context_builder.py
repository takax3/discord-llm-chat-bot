from discordbot.domain.conversation_message import ConversationMessage
from discordbot.constants import DEFAULT_MAX_RESPONSE_CHARS
from discordbot.services.context_builder import ContextBuilder


def test_build_messages_includes_prior_chain_and_current_user_message() -> None:
    builder = ContextBuilder(
        system_prompt="system",
        max_response_chars=DEFAULT_MAX_RESPONSE_CHARS,
    )

    messages = builder.build_messages(
        prior_messages=[
            ConversationMessage(
                discord_message_id=1,
                reply_to_message_id=None,
                guild_id=1,
                channel_id=10,
                user_id=100,
                role="user",
                content="hello",
            ),
            ConversationMessage(
                discord_message_id=2,
                reply_to_message_id=1,
                guild_id=1,
                channel_id=10,
                user_id=999,
                role="assistant",
                content="hi",
            ),
        ],
        user_message="follow up",
    )

    assert messages == [
        {
            "role": "system",
            "content": (
                "system\n\n"
                f"Keep your final response within {DEFAULT_MAX_RESPONSE_CHARS} characters."
            ),
        },
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
        {"role": "user", "content": "follow up"},
    ]
