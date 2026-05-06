from __future__ import annotations

import sqlite3

from discordbot.domain.conversation_message import ConversationMessage


class ConversationRepository:
    def __init__(self, *, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def save_message(self, message: ConversationMessage) -> None:
        self._connection.execute(
            """
            INSERT OR REPLACE INTO conversation_messages (
                discord_message_id,
                reply_to_message_id,
                guild_id,
                channel_id,
                user_id,
                role,
                content
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                message.discord_message_id,
                message.reply_to_message_id,
                message.guild_id,
                message.channel_id,
                message.user_id,
                message.role,
                message.content,
            ),
        )
        self._connection.commit()

    def get_message(self, discord_message_id: int) -> ConversationMessage | None:
        row = self._connection.execute(
            """
            SELECT
                discord_message_id,
                reply_to_message_id,
                guild_id,
                channel_id,
                user_id,
                role,
                content
            FROM conversation_messages
            WHERE discord_message_id = ?
            """,
            (discord_message_id,),
        ).fetchone()
        if row is None:
            return None
        return ConversationMessage(
            discord_message_id=int(row[0]),
            reply_to_message_id=int(row[1]) if row[1] is not None else None,
            guild_id=int(row[2]),
            channel_id=int(row[3]),
            user_id=int(row[4]),
            role=str(row[5]),
            content=str(row[6]),
        )

    def get_reply_chain(
        self,
        *,
        start_message_id: int,
        limit: int,
    ) -> list[ConversationMessage]:
        chain: list[ConversationMessage] = []
        current_message_id: int | None = start_message_id
        while current_message_id is not None and len(chain) < limit:
            message = self.get_message(current_message_id)
            if message is None:
                break
            chain.append(message)
            current_message_id = message.reply_to_message_id
        chain.reverse()
        return chain
