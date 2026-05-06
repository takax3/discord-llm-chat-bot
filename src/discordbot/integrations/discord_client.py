from __future__ import annotations

import logging

import discord

from discordbot.config import AppConfig
from discordbot.messages import format_message
from discordbot.services.chat_service import ChatService
from discordbot.storage.settings_repository import SettingsRepository


def build_discord_client(
    *,
    config: AppConfig,
    logger: logging.Logger,
    settings_repository: SettingsRepository,
) -> discord.Client:
    intents = discord.Intents.default()
    intents.message_content = True
    return DiscordBotClient(
        config=config,
        chat_service=ChatService(mention_response=config.mention_response),
        intents=intents,
        logger=logger,
        settings_repository=settings_repository,
    )


class DiscordBotClient(discord.Client):
    def __init__(
        self,
        *,
        config: AppConfig,
        chat_service: ChatService,
        logger: logging.Logger,
        settings_repository: SettingsRepository,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self._config = config
        self._chat_service = chat_service
        self._logger = logger
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
        if not self._chat_service.should_respond(
            mentioned_user_ids=message.raw_mentions,
            bot_user_id=self.user.id,
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

        self._logger.info(
            format_message(
                "mention_received",
                user_id=message.author.id,
                channel_id=message.channel.id,
            )
        )
        reply = self._chat_service.build_reply(
            message_content=message.content,
            bot_user_id=self.user.id,
        )
        sent_message = await message.reply(reply, mention_author=False)
        self._logger.info(format_message("reply_sent", message_id=sent_message.id))
