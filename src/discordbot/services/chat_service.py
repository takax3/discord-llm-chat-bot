from __future__ import annotations

import re
from dataclasses import dataclass

from discordbot.constants import DEFAULT_OLLAMA_ERROR_RESPONSE
from discordbot.domain.guild_settings import GuildSettings
from discordbot.domain.search_result import SearchResult
from discordbot.messages import format_message


def remove_bot_mention(message_content: str, bot_user_id: int) -> str:
    mention_pattern = re.compile(rf"<@!?{bot_user_id}>")
    without_mention = mention_pattern.sub("", message_content)
    return " ".join(without_mention.split()).strip()


@dataclass(frozen=True)
class ChatService:
    mention_response: str
    max_response_chars: int
    vision_image_only_prompt: str

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

    def build_image_only_prompt(self) -> str:
        return self.vision_image_only_prompt

    def build_thinking_reply(self, queue_ahead: int) -> str:
        return format_message("thinking", queue_ahead=queue_ahead)

    def build_ollama_error_reply(self) -> str:
        return DEFAULT_OLLAMA_ERROR_RESPONSE

    def normalize_reply(self, reply: str) -> str:
        return self.normalize_reply_with_sources(reply, [])

    def normalize_reply_with_sources(
        self,
        reply: str,
        sources: list[SearchResult],
    ) -> str:
        stripped_reply = reply.strip()
        sources = sources[:3]
        reference_block = self._build_reference_block(sources)
        if not reference_block:
            if len(stripped_reply) <= self.max_response_chars:
                return stripped_reply
            suffix = "\n..."
            truncated_length = max(self.max_response_chars - len(suffix), 1)
            return f"{stripped_reply[:truncated_length].rstrip()}{suffix}"

        available_for_reply = self.max_response_chars - len(reference_block)
        if available_for_reply < 1:
            return reference_block[: self.max_response_chars].rstrip()
        if len(stripped_reply) > available_for_reply:
            suffix = "\n..."
            truncated_length = max(available_for_reply - len(suffix), 1)
            stripped_reply = f"{stripped_reply[:truncated_length].rstrip()}{suffix}"
        return f"{stripped_reply}{reference_block}"

    def _build_reference_block(self, sources: list[SearchResult]) -> str:
        if not sources:
            return ""
        lines = ["", "", "参考URL:"]
        for index, source in enumerate(sources, start=1):
            lines.append(f"{index}. {source.url}")
        return "\n".join(lines)
