from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

import discord
from discord import app_commands

from discordbot.config import AppConfig
from discordbot.domain.conversation_message import ConversationMessage
from discordbot.domain.inference_log import InferenceLog
from discordbot.domain.search_result import SearchResult
from discordbot.integrations.brave_search_client import BraveSearchClient, BraveSearchClientError
from discordbot.integrations.ollama_client import OllamaClient, OllamaClientError
from discordbot.messages import format_message
from discordbot.services.chat_service import ChatService
from discordbot.services.context_builder import ContextBuilder
from discordbot.services.image_preprocessor import ImagePreprocessor, ImagePreprocessorError
from discordbot.services.gpu_power_sampler import GpuPowerSampler
from discordbot.services.inference_queue import InferenceQueue
from discordbot.services.presence_service import PresenceService
from discordbot.services.search_decision_service import SearchDecisionService
from discordbot.storage.conversation_repository import ConversationRepository
from discordbot.storage.inference_log_repository import InferenceLogRepository
from discordbot.storage.settings_repository import SettingsRepository
from discordbot.webhook_logging import DiscordWebhookNotifier

def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _elapsed_seconds(start: str | None, end: str | None) -> float | None:
    if start is None or end is None:
        return None
    return (datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds()


def build_discord_client(
    *,
    config: AppConfig,
    logger: logging.Logger,
    ollama_client: OllamaClient,
    conversation_repository: ConversationRepository,
    settings_repository: SettingsRepository,
    inference_log_repository: InferenceLogRepository,
    gpu_power_sampler: GpuPowerSampler,
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
            vision_image_only_prompt=config.vision_image_only_prompt,
        ),
        intents=intents,
        logger=logger,
        ollama_client=ollama_client,
        brave_search_client=BraveSearchClient(
            api_key=config.brave_search_api_key,
            max_results=config.web_search_max_results,
            timeout_seconds=config.web_search_timeout_seconds,
            country=config.web_search_country,
            language=config.web_search_language,
        ),
        context_builder=ContextBuilder(
            system_prompt=config.system_prompt,
            max_response_chars=config.max_response_chars,
        ),
        conversation_repository=conversation_repository,
        settings_repository=settings_repository,
        inference_log_repository=inference_log_repository,
        gpu_power_sampler=gpu_power_sampler,
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
        brave_search_client: BraveSearchClient,
        context_builder: ContextBuilder,
        conversation_repository: ConversationRepository,
        settings_repository: SettingsRepository,
        inference_log_repository: InferenceLogRepository,
        gpu_power_sampler: GpuPowerSampler,
        webhook_notifier: DiscordWebhookNotifier,
        app_version: str,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self._config = config
        self._chat_service = chat_service
        self._logger = logger
        self._ollama_client = ollama_client
        self._brave_search_client = brave_search_client
        self._context_builder = context_builder
        self._conversation_repository = conversation_repository
        self._settings_repository = settings_repository
        self._inference_log_repository = inference_log_repository
        self._gpu_power_sampler = gpu_power_sampler
        self._webhook_notifier = webhook_notifier
        self._app_version = app_version
        self._shutdown_signal_name = "unknown"
        self._is_closing = False
        self._ready_notified = False
        self._inference_queue = InferenceQueue()
        self._presence_service = PresenceService(model=config.ollama_model)
        self._search_decision_service = SearchDecisionService(
            ollama_client=ollama_client,
        )
        self._image_preprocessor = ImagePreprocessor(
            max_pixels=config.vision_max_pixels,
        )
        self._tree = app_commands.CommandTree(self)
        self._register_slash_commands()

    async def setup_hook(self) -> None:
        await self._tree.sync()

    def _register_slash_commands(self) -> None:
        @self._tree.command(name="stats", description="このチャンネルの最後の推論統計を表示")
        async def stats(interaction: discord.Interaction) -> None:
            if interaction.channel_id is None:
                await interaction.response.send_message(
                    "チャンネル情報を取得できませんでした。"
                )
                return
            log = self._inference_log_repository.fetch_last_by_channel(interaction.channel_id)
            if log is None:
                await interaction.response.send_message(
                    "このチャンネルにはまだ推論ログがありません。"
                )
                return

            lines: list[str] = ["**最後の推論ログ（このチャンネル）**"]

            lines.append(f"メッセージ受信: {log.message_received_at}")

            stage1 = _elapsed_seconds(log.decision_started_at, log.decision_ended_at)
            if stage1 is not None:
                tokens = ""
                if log.decision_prompt_tokens is not None and log.decision_completion_tokens is not None:
                    tokens = f" | prompt {log.decision_prompt_tokens} + completion {log.decision_completion_tokens} トークン"
                lines.append(f"Stage 1（検索判定）: {stage1:.2f} 秒{tokens}")

            if log.search_query_count > 0:
                lines.append(f"検索クエリ数: {log.search_query_count}")

            stage2 = _elapsed_seconds(log.inference_started_at, log.inference_ended_at)
            if stage2 is not None:
                tokens = ""
                if log.inference_prompt_tokens is not None and log.inference_completion_tokens is not None:
                    tokens = f" | prompt {log.inference_prompt_tokens} + completion {log.inference_completion_tokens} トークン"
                lines.append(f"Stage 2（推論）: {stage2:.2f} 秒{tokens}")
            elif log.is_error:
                lines.append("Stage 2（推論）: エラー終了")

            if log.reply_sent_at is not None:
                lines.append(f"返信完了: {log.reply_sent_at}")

            if log.gpu_avg_watts is not None:
                energy = f" / {log.gpu_energy_joules / 3_600_000:.5f} kWh" if log.gpu_energy_joules is not None else ""
                lines.append(f"GPU 消費電力: {log.gpu_avg_watts:.1f} W{energy}")

            await interaction.response.send_message("\n".join(lines))

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
        user_images = await self._extract_user_images(message)
        if not user_message and user_images:
            user_message = self._chat_service.build_image_only_prompt()
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
                suppress_embeds=True,
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

        message_received_at = _now_utc()
        decision_started_at: str | None = None
        decision_ended_at: str | None = None
        search_started_at: str | None = None
        search_ended_at: str | None = None
        inference_started_at: str | None = None
        inference_ended_at: str | None = None
        reply_sent_at: str | None = None
        decision_prompt_tokens: int | None = None
        decision_completion_tokens: int | None = None
        search_query_count = 0
        inference_prompt_tokens: int | None = None
        inference_completion_tokens: int | None = None
        is_error = False
        gpu_samples: list[float] = []
        gpu_stop = asyncio.Event()
        gpu_task: asyncio.Task[None] | None = None
        turn_start_time: datetime | None = None

        async def _poll_gpu() -> None:
            while not gpu_stop.is_set():
                w = self._gpu_power_sampler.read_watts()
                if w is not None:
                    gpu_samples.append(w)
                try:
                    await asyncio.wait_for(asyncio.shield(gpu_stop.wait()), timeout=1.0)
                except asyncio.TimeoutError:
                    pass

        ticket, queue_ahead = await self._inference_queue.reserve()
        await self._sync_presence_from_queue()
        turn_started = False
        try:
            sent_message = await message.reply(
                self._chat_service.build_thinking_reply(queue_ahead),
                mention_author=False,
                suppress_embeds=True,
            )
            while queue_ahead > 0:
                queue_ahead = await self._inference_queue.wait_for_ahead_change(
                    ticket=ticket,
                    previous_ahead=queue_ahead,
                )
                await sent_message.edit(
                    content=self._chat_service.build_thinking_reply(queue_ahead),
                    suppress=True,
                )
            turn_started = True
            turn_start_time = datetime.now(timezone.utc)
            if self._gpu_power_sampler.available:
                gpu_task = asyncio.create_task(_poll_gpu())
            prior_messages = self._build_prior_messages(message)
            try:
                show_steps = self._config.show_steps
                completed_lines: list[str] = []
                search_results: list[SearchResult] = []

                def _with_pending(text: str) -> str:
                    if show_steps and completed_lines:
                        return "\n".join(completed_lines + [text])
                    return text

                if self._config.web_search_enabled:
                    # Stage 1: メインモデルが検索要否とクエリ（複数可）を1回で判定する
                    await sent_message.edit(
                        content=_with_pending(format_message("deciding")), suppress=True
                    )
                    decision_started_at = _now_utc()
                    decision = await self._search_decision_service.decide(
                        prior_messages=prior_messages,
                        user_message=user_message,
                        user_images=user_images,
                    )
                    decision_ended_at = _now_utc()
                    decision_prompt_tokens = decision.prompt_tokens
                    decision_completion_tokens = decision.completion_tokens
                    if decision.action == "search" and decision.search_queries:
                        queries_text = ", ".join(decision.search_queries)
                        if show_steps:
                            completed_lines.append(format_message("search_queries_decided", queries=queries_text))
                        await sent_message.edit(
                            content=_with_pending(format_message("searching")),
                            suppress=True,
                        )
                        search_query_count = len(decision.search_queries)
                        search_started_at = _now_utc()
                        results_list = await asyncio.gather(
                            *[
                                self._brave_search_client.search(q)
                                for q in decision.search_queries
                            ],
                            return_exceptions=True,
                        )
                        search_ended_at = _now_utc()
                        for r in results_list:
                            if isinstance(r, list):
                                search_results.extend(r)
                            elif isinstance(r, BraveSearchClientError):
                                self._logger.warning(
                                    format_message("web_search_failed", query=str(r))
                                )
                        if show_steps:
                            completed_lines.append(format_message("search_completed"))
                        await sent_message.edit(
                            content="\n".join(completed_lines) if completed_lines else format_message("search_completed"),
                            suppress=True,
                        )
                    elif show_steps:
                        completed_lines.append(format_message("search_not_needed"))
                # Stage 2: 常にメインモデルで最終回答を生成（推論中を表示）
                await sent_message.edit(
                    content=_with_pending(format_message("inferring")), suppress=True
                )
                ollama_messages = self._context_builder.build_messages(
                    prior_messages=prior_messages,
                    user_message=user_message,
                    user_images=user_images,
                    search_results=search_results,
                )
                inference_started_at = _now_utc()
                result = await self._ollama_client.generate_reply(ollama_messages)
                inference_ended_at = _now_utc()
                inference_prompt_tokens = result.prompt_tokens
                inference_completion_tokens = result.completion_tokens
                reply = result.content
                self._presence_service.set_tokens_per_second(result.tokens_per_second)
                reply = self._chat_service.normalize_reply_with_sources(reply, search_results)
                if show_steps:
                    completed_lines.append(format_message("inferring_done"))
                if show_steps and completed_lines:
                    reply = "\n".join(completed_lines) + "\n\n" + reply
            except OllamaClientError:
                self._logger.warning(
                    format_message(
                        "ollama_fallback",
                        channel_id=message.channel.id,
                    )
                )
                is_error = True
                reply = self._chat_service.build_ollama_error_reply()
        finally:
            if turn_started:
                await self._inference_queue.finish_turn(ticket)
            else:
                await self._inference_queue.cancel(ticket)
            await self._sync_presence_from_queue()
        await sent_message.edit(content=reply, suppress=True)
        reply_sent_at = _now_utc()
        if gpu_task is not None:
            gpu_stop.set()
            await gpu_task
        elapsed_seconds = (
            (datetime.now(timezone.utc) - turn_start_time).total_seconds()
            if turn_start_time is not None
            else None
        )
        gpu_avg_watts = sum(gpu_samples) / len(gpu_samples) if gpu_samples else None
        gpu_energy_joules = (
            gpu_avg_watts * elapsed_seconds
            if gpu_avg_watts is not None and elapsed_seconds is not None
            else None
        )
        self._inference_log_repository.save(
            InferenceLog(
                guild_id=message.guild.id,
                channel_id=message.channel.id,
                user_id=message.author.id,
                message_received_at=message_received_at,
                decision_started_at=decision_started_at,
                decision_ended_at=decision_ended_at,
                search_started_at=search_started_at,
                search_ended_at=search_ended_at,
                inference_started_at=inference_started_at,
                inference_ended_at=inference_ended_at,
                reply_sent_at=reply_sent_at,
                decision_prompt_tokens=decision_prompt_tokens,
                decision_completion_tokens=decision_completion_tokens,
                search_query_count=search_query_count,
                inference_prompt_tokens=inference_prompt_tokens,
                inference_completion_tokens=inference_completion_tokens,
                is_error=is_error,
                gpu_avg_watts=gpu_avg_watts,
                gpu_energy_joules=gpu_energy_joules,
            )
        )
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

    async def _extract_user_images(self, message: discord.Message) -> list[str]:
        if not self._config.vision_enabled:
            return []
        for attachment in message.attachments:
            if not self._image_preprocessor.is_supported_attachment(
                content_type=attachment.content_type,
                filename=attachment.filename,
            ):
                continue
            try:
                raw_bytes = await attachment.read(use_cached=True)
                return [self._image_preprocessor.encode_for_ollama(raw_bytes)]
            except (discord.DiscordException, ImagePreprocessorError):
                self._logger.exception("Failed to process image attachment.")
                return []
        return []

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
