from __future__ import annotations

import logging

import discord

from discordbot.config import AppConfig
from discordbot.domain.conversation_message import ConversationMessage
from discordbot.integrations.ollama_client import OllamaClient, OllamaClientError
from discordbot.messages import format_message
from discordbot.services.chat_service import ChatService
from discordbot.services.context_builder import ContextBuilder
from discordbot.storage.conversation_repository import ConversationRepository
from discordbot.storage.settings_repository import SettingsRepository


def build_discord_client(
    *,
    config: AppConfig,
    logger: logging.Logger,
    ollama_client: OllamaClient,
    conversation_repository: ConversationRepository,
    settings_repository: SettingsRepository,
) -> discord.Client:
    intents = discord.Intents.default()
    intents.message_content = True
    return DiscordBotClient(
        config=config,
        chat_service=ChatService(
            mention_response=config.mention_response,
            max_response_chars=config.max_response_chars,
        ),
        intents=intents,
        logger=logger,
        ollama_client=ollama_client,
        context_builder=ContextBuilder(
            system_prompt=config.system_prompt,
            max_response_chars=config.max_response_chars,
        ),
        conversation_repository=conversation_repository,
        settings_repository=settings_repository,
    )


class DiscordBotClient(discord.Client):
    def __init__(
        self,
        *,
        config: AppConfig,
        chat_service: ChatService,
        logger: logging.Logger,
        ollama_client: OllamaClient,
        context_builder: ContextBuilder,
        conversation_repository: ConversationRepository,
        settings_repository: SettingsRepository,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self._config = config
        self._chat_service = chat_service
        self._logger = logger
        self._ollama_client = ollama_client
        self._context_builder = context_builder
        self._conversation_repository = conversation_repository
        self._settings_repository = settings_repository

    async def on_ready(self) -> None:
        if self.user is None:
            return
        self._logger.info(format_message("discord_ready", user=str(self.user)))

    async def on_message(self, message: discord.Message) -> None:
        if self.user is None:
            return
        if message.author.bot or message.author.id == self.user.id:
            return
        if message.guild is None:
            return
        is_reply_to_bot = await self._is_reply_to_bot_message(message)
        if not self._chat_service.should_respond(
            mentioned_user_ids=message.raw_mentions,
            bot_user_id=self.user.id,
            is_reply_to_bot=is_reply_to_bot,
        ):
            return

        guild_settings = self._settings_repository.get_guild_settings(message.guild.id)
        if not guild_settings.is_enabled:
            self._logger.info(
                format_message("guild_disabled", guild_id=message.guild.id)
            )
            return
        if not self._chat_service.is_guild_message_allowed(
            guild_settings=guild_settings,
            channel_id=message.channel.id,
        ):
            self._logger.info(
                format_message(
                    "channel_not_allowed",
                    channel_id=message.channel.id,
                    guild_id=message.guild.id,
                )
            )
            return

        if is_reply_to_bot and message.reference is not None:
            self._logger.info(
                format_message(
                    "reply_context_received",
                    user_id=message.author.id,
                    channel_id=message.channel.id,
                    reference_message_id=message.reference.message_id,
                )
            )
        else:
            self._logger.info(
                format_message(
                    "mention_received",
                    user_id=message.author.id,
                    channel_id=message.channel.id,
                )
            )
        user_message = self._chat_service.extract_user_message(
            message_content=message.content,
            bot_user_id=self.user.id,
        )
        self._save_conversation_message(
            ConversationMessage(
                discord_message_id=message.id,
                reply_to_message_id=message.reference.message_id
                if message.reference is not None
                else None,
                guild_id=message.guild.id,
                channel_id=message.channel.id,
                user_id=message.author.id,
                role="user",
                content=user_message or message.content,
            )
        )
        if not user_message:
            sent_message = await message.reply(
                self._chat_service.build_empty_message_reply(),
                mention_author=False,
            )
            self._save_conversation_message(
                ConversationMessage(
                    discord_message_id=sent_message.id,
                    reply_to_message_id=message.id,
                    guild_id=message.guild.id,
                    channel_id=message.channel.id,
                    user_id=self.user.id,
                    role="assistant",
                    content=self._chat_service.build_empty_message_reply(),
                )
            )
            self._logger.info(format_message("reply_sent", message_id=sent_message.id))
            return

        sent_message = await message.reply(
            self._chat_service.build_thinking_reply(),
            mention_author=False,
        )
        prior_messages = self._build_prior_messages(message)
        ollama_messages = self._context_builder.build_messages(
            prior_messages=prior_messages,
            user_message=user_message,
        )
        try:
            reply = await self._ollama_client.generate_reply(ollama_messages)
        except OllamaClientError:
            self._logger.warning(
                format_message(
                    "ollama_fallback",
                    channel_id=message.channel.id,
                )
            )
            reply = self._chat_service.build_ollama_error_reply()
        reply = self._chat_service.normalize_reply(reply)
        await sent_message.edit(content=reply)
        self._save_conversation_message(
            ConversationMessage(
                discord_message_id=sent_message.id,
                reply_to_message_id=message.id,
                guild_id=message.guild.id,
                channel_id=message.channel.id,
                user_id=self.user.id,
                role="assistant",
                content=reply,
            )
        )
        self._logger.info(format_message("reply_sent", message_id=sent_message.id))

    async def _is_reply_to_bot_message(self, message: discord.Message) -> bool:
        if self.user is None or message.reference is None or message.reference.message_id is None:
            return False
        resolved = message.reference.resolved
        if isinstance(resolved, discord.Message):
            return resolved.author.id == self.user.id
        stored_message = self._conversation_repository.get_message(message.reference.message_id)
        if stored_message is None:
            return False
        return stored_message.role == "assistant"

    def _build_prior_messages(self, message: discord.Message) -> list[ConversationMessage]:
        if message.reference is None or message.reference.message_id is None:
            return []
        return self._conversation_repository.get_reply_chain(
            start_message_id=message.reference.message_id,
            limit=self._config.max_history_messages,
        )

    def _save_conversation_message(self, message: ConversationMessage) -> None:
        self._conversation_repository.save_message(message)
        self._logger.info(
            format_message(
                "conversation_message_saved",
                message_id=message.discord_message_id,
                role=message.role,
            )
        )
