from discordbot.domain.conversation_message import ConversationMessage
from discordbot.constants import DEFAULT_MAX_RESPONSE_CHARS
from discordbot.domain.search_result import SearchResult
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

    assert len(messages) == 4
    system_content = messages[0]["content"]
    assert messages[0]["role"] == "system"
    assert system_content.startswith("system\n\n")
    assert "The current date and time is " in system_content
    assert "JST" in system_content
    assert "If you do not know something" in system_content
    assert f"Keep your final response within {DEFAULT_MAX_RESPONSE_CHARS} characters." in system_content
    assert messages[1] == {"role": "user", "content": "hello"}
    assert messages[2] == {"role": "assistant", "content": "hi"}
    assert messages[3] == {"role": "user", "content": "follow up"}


def test_build_messages_includes_images_for_current_user_message() -> None:
    builder = ContextBuilder(
        system_prompt="system",
        max_response_chars=DEFAULT_MAX_RESPONSE_CHARS,
    )

    messages = builder.build_messages(
        prior_messages=[],
        user_message="what is in this image?",
        user_images=["base64-image-data"],
    )

    assert messages[-1] == {
        "role": "user",
        "content": "what is in this image?",
        "images": ["base64-image-data"],
    }


def test_build_messages_includes_search_results_in_user_content() -> None:
    builder = ContextBuilder(
        system_prompt="system",
        max_response_chars=DEFAULT_MAX_RESPONSE_CHARS,
    )

    messages = builder.build_messages(
        prior_messages=[],
        user_message="latest news",
        search_results=[
            SearchResult(
                title="News title",
                url="https://example.com/news",
                snippet="short summary",
            )
        ],
    )

    assert "Web search results" in str(messages[-1]["content"])
    assert "https://example.com/news" in str(messages[-1]["content"])
