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
                "If you do not know something, say clearly that you do not know instead of guessing. "
                "Do not invent facts that are not supported by the conversation context. "
                "If you are uncertain, say that it is a guess or needs confirmation. "
                "For medical, legal, financial, security, or privacy-sensitive topics, avoid definitive claims and present general information with appropriate caution. "
                "Reply concisely unless the user explicitly asks for a detailed explanation. "
                "Reply in Japanese unless the user explicitly asks for another language.\n"
                f"Keep your final response within {DEFAULT_MAX_RESPONSE_CHARS} characters."
            ),
        },
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
        {"role": "user", "content": "follow up"},
    ]
