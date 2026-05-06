from __future__ import annotations

import asyncio
import logging
import signal

import discord

from discordbot.config import AppConfig, load_config
from discordbot.integrations.discord_client import build_discord_client
from discordbot.integrations.ollama_client import OllamaClient
from discordbot.messages import format_message
from discordbot.storage.conversation_repository import ConversationRepository
from discordbot.storage.database import initialize_database
from discordbot.storage.settings_repository import SettingsRepository
from discordbot.version import get_app_version
from discordbot.webhook_logging import DiscordWebhookHandler, DiscordWebhookNotifier

APP_VERSION = get_app_version()


def _configure_logging(log_level: str) -> logging.Logger:
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s.%(msecs)03d %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger(__name__)


async def _run_bot(config: AppConfig, logger: logging.Logger) -> None:
    database_connection = initialize_database(config.sqlite_path)
    webhook_notifier = DiscordWebhookNotifier(
        webhook_url=config.discord_webhook_url,
        minimum_level_name=config.discord_webhook_notify_logs_min_level,
        notify_startup=config.discord_webhook_notify_startup,
        notify_shutdown=config.discord_webhook_notify_shutdown,
        notify_logs=config.discord_webhook_notify_logs,
    )
    webhook_handler = DiscordWebhookHandler(webhook_notifier)
    root_logger = logging.getLogger()
    root_logger.addHandler(webhook_handler)
    logger.info(
        format_message("startup", version=APP_VERSION),
        extra={"skip_webhook": True},
    )
    logger.info(format_message("database_ready", sqlite_path=str(config.sqlite_path)))

    settings_repository = SettingsRepository(
        connection=database_connection,
        config=config,
    )
    conversation_repository = ConversationRepository(connection=database_connection)
    ollama_client = OllamaClient.from_config(config)
    client = build_discord_client(
        config=config,
        logger=logger,
        ollama_client=ollama_client,
        conversation_repository=conversation_repository,
        settings_repository=settings_repository,
        webhook_notifier=webhook_notifier,
        app_version=APP_VERSION,
    )

    loop = asyncio.get_running_loop()
    _register_signal_handlers(loop=loop, client=client, logger=logger)

    try:
        await client.start(config.discord_bot_token)
    finally:
        await webhook_notifier.close()
        root_logger.removeHandler(webhook_handler)
        database_connection.close()


def _register_signal_handlers(
    *,
    loop: asyncio.AbstractEventLoop,
    client: discord.Client,
    logger: logging.Logger,
) -> None:
    def request_shutdown(shutdown_signal: signal.Signals) -> None:
        if hasattr(client, "set_shutdown_signal_name"):
            client.set_shutdown_signal_name(shutdown_signal.name)
        logger.info(format_message("shutdown_requested", signal_name=shutdown_signal.name))
        asyncio.create_task(client.close())

    for shutdown_signal in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(
                shutdown_signal,
                request_shutdown,
                shutdown_signal,
            )
        except NotImplementedError:
            logger.warning(
                format_message(
                    "signal_handler_not_supported",
                    signal_name=shutdown_signal.name,
                )
            )


def main() -> None:
    config = load_config()
    logger = _configure_logging(config.log_level)
    asyncio.run(_run_bot(config, logger))


if __name__ == "__main__":
    main()
