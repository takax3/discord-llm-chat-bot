from __future__ import annotations

import re
from dataclasses import dataclass

from discordbot.domain.guild_settings import GuildSettings


def remove_bot_mention(message_content: str, bot_user_id: int) -> str:
    mention_pattern = re.compile(rf"<@!?{bot_user_id}>")
    without_mention = mention_pattern.sub("", message_content)
    return " ".join(without_mention.split()).strip()


@dataclass(frozen=True)
class ChatService:
    mention_response: str

    def is_guild_message_allowed(
        self,
        *,
        guild_settings: GuildSettings,
        channel_id: int,
    ) -> bool:
        if not guild_settings.is_enabled:
            return False
        if not guild_settings.allowed_channel_ids:
            return True
        return channel_id in guild_settings.allowed_channel_ids

    def should_respond(
        self,
        *,
        mentioned_user_ids: list[int],
        bot_user_id: int,
    ) -> bool:
        return bot_user_id in mentioned_user_ids

    def build_reply(
        self,
        *,
        message_content: str,
        bot_user_id: int,
    ) -> str:
        normalized_content = remove_bot_mention(message_content, bot_user_id)
        if normalized_content:
            return f"{self.mention_response}\n\nYou said: {normalized_content}"
        return self.mention_response
