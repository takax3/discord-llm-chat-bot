from __future__ import annotations

import logging

import discord

from discordbot.config import AppConfig
from discordbot.domain.conversation_message import ConversationMessage
from discordbot.integrations.ollama_client import OllamaClient, OllamaClientError
from discordbot.messages import format_message
from discordbot.services.chat_service import ChatService
from discordbot.services.context_builder import ContextBuilder
from discordbot.services.inference_queue import InferenceQueue
from discordbot.services.presence_service import PresenceService
from discordbot.storage.conversation_repository import ConversationRepository
from discordbot.storage.settings_repository import SettingsRepository
from discordbot.webhook_logging import DiscordWebhookNotifier


def build_discord_client(
    *,
    config: AppConfig,
    logger: logging.Logger,
    ollama_client: OllamaClient,
    conversation_repository: ConversationRepository,
    settings_repository: SettingsRepository,
    webhook_notifier: DiscordWebhookNotifier,
    app_version: str,
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
        webhook_notifier=webhook_notifier,
        app_version=app_version,
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
        webhook_notifier: DiscordWebhookNotifier,
        app_version: str,
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
        self._webhook_notifier = webhook_notifier
        self._app_version = app_version
        self._shutdown_signal_name = "unknown"
        self._is_closing = False
        self._ready_notified = False
        self._inference_queue = InferenceQueue()
        self._presence_service = PresenceService()

    async def on_ready(self) -> None:
        if self.user is None:
            return
        self._logger.info(format_message("discord_ready", user=str(self.user)))
        await self._sync_presence()
        if not self._ready_notified:
            await self._webhook_notifier.send_ready(
                version=self._app_version,
                guild_count=len(self.guilds),
                model=self._config.ollama_model,
            )
            self._ready_notified = True

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

        ticket, queue_ahead = await self._inference_queue.reserve()
        await self._sync_presence_from_queue()
        turn_started = False
        try:
            sent_message = await message.reply(
                self._chat_service.build_thinking_reply(queue_ahead),
                mention_author=False,
            )
            while queue_ahead > 0:
                queue_ahead = await self._inference_queue.wait_for_ahead_change(
                    ticket=ticket,
                    previous_ahead=queue_ahead,
                )
                await sent_message.edit(
                    content=self._chat_service.build_thinking_reply(queue_ahead)
                )
            turn_started = True
            prior_messages = self._build_prior_messages(message)
            ollama_messages = self._context_builder.build_messages(
                prior_messages=prior_messages,
                user_message=user_message,
            )
            try:
                result = await self._ollama_client.generate_reply(ollama_messages)
                reply = result.content
                self._presence_service.set_tokens_per_second(result.tokens_per_second)
            except OllamaClientError:
                self._logger.warning(
                    format_message(
                        "ollama_fallback",
                        channel_id=message.channel.id,
                    )
                )
                reply = self._chat_service.build_ollama_error_reply()
        finally:
            if turn_started:
                await self._inference_queue.finish_turn(ticket)
            else:
                await self._inference_queue.cancel(ticket)
            await self._sync_presence_from_queue()
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

    def set_shutdown_signal_name(self, signal_name: str) -> None:
        self._shutdown_signal_name = signal_name

    async def close(self) -> None:
        if self._is_closing:
            return
        self._is_closing = True
        self._logger.info(
            format_message("shutdown_started", signal_name=self._shutdown_signal_name),
            extra={"skip_webhook": True},
        )
        await self._webhook_notifier.send_shutdown(
            signal_name=self._shutdown_signal_name,
            guild_count=len(self.guilds),
        )
        if not self.is_closed():
            try:
                await self.change_presence(
                    status=discord.Status.offline,
                    activity=None,
                )
                self._logger.info(
                    format_message("presence_offline"),
                    extra={"skip_webhook": True},
                )
            except discord.DiscordException:
                self._logger.exception(format_message("presence_offline_failed"))
        await super().close()

    async def _sync_presence_from_queue(self) -> None:
        status = await self._inference_queue.get_status()
        self._presence_service.set_queue_count(status.waiting_count)
        await self._sync_presence()

    async def _sync_presence(self) -> None:
        if self.user is None or self.is_closed():
            return
        status_text = self._presence_service.build_status_text()
        try:
            await self.change_presence(
                status=discord.Status.online,
                activity=self._presence_service.build_activity(),
            )
            self._logger.info(
                format_message("presence_updated", status_text=status_text),
                extra={"skip_webhook": True},
            )
        except discord.DiscordException:
            self._logger.exception(format_message("presence_update_failed"))
