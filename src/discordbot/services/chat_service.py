from __future__ import annotations

import re
from dataclasses import dataclass

from discordbot.constants import DEFAULT_OLLAMA_ERROR_RESPONSE
from discordbot.domain.guild_settings import GuildSettings
from discordbot.messages import format_message


def remove_bot_mention(message_content: str, bot_user_id: int) -> str:
    mention_pattern = re.compile(rf"<@!?{bot_user_id}>")
    without_mention = mention_pattern.sub("", message_content)
    return " ".join(without_mention.split()).strip()


@dataclass(frozen=True)
class ChatService:
    mention_response: str
    max_response_chars: int

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
        is_reply_to_bot: bool,
    ) -> bool:
        return bot_user_id in mentioned_user_ids or is_reply_to_bot

    def extract_user_message(
        self,
        *,
        message_content: str,
        bot_user_id: int,
    ) -> str:
        return remove_bot_mention(message_content, bot_user_id)

    def build_empty_message_reply(self) -> str:
        return self.mention_response

    def build_thinking_reply(self, queue_ahead: int) -> str:
        return format_message("thinking", queue_ahead=queue_ahead)

    def build_ollama_error_reply(self) -> str:
        return DEFAULT_OLLAMA_ERROR_RESPONSE

    def normalize_reply(self, reply: str) -> str:
        stripped_reply = reply.strip()
        if len(stripped_reply) <= self.max_response_chars:
            return stripped_reply

        suffix = "\n..."
        truncated_length = max(self.max_response_chars - len(suffix), 1)
        return f"{stripped_reply[:truncated_length].rstrip()}{suffix}"
