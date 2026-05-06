from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConversationMessage:
    discord_message_id: int
    reply_to_message_id: int | None
    guild_id: int
    channel_id: int
    user_id: int
    role: str
    content: str
