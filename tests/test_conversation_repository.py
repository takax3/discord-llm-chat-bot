import sqlite3

from discordbot.domain.conversation_message import ConversationMessage
from discordbot.storage.conversation_repository import ConversationRepository


def test_get_reply_chain_returns_messages_in_chronological_order() -> None:
    connection = sqlite3.connect(":memory:")
    connection.execute(
        """
        CREATE TABLE conversation_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            discord_message_id INTEGER NOT NULL UNIQUE,
            reply_to_message_id INTEGER,
            guild_id INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    repository = ConversationRepository(connection=connection)
    repository.save_message(
        ConversationMessage(
            discord_message_id=1,
            reply_to_message_id=None,
            guild_id=1,
            channel_id=10,
            user_id=100,
            role="user",
            content="first",
        )
    )
    repository.save_message(
        ConversationMessage(
            discord_message_id=2,
            reply_to_message_id=1,
            guild_id=1,
            channel_id=10,
            user_id=999,
            role="assistant",
            content="second",
        )
    )
    repository.save_message(
        ConversationMessage(
            discord_message_id=3,
            reply_to_message_id=2,
            guild_id=1,
            channel_id=10,
            user_id=100,
            role="user",
            content="third",
        )
    )

    chain = repository.get_reply_chain(start_message_id=3, limit=10)

    assert [message.discord_message_id for message in chain] == [1, 2, 3]
