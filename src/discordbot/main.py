import logging

from discordbot.config import load_config
from discordbot.integrations.discord_client import build_discord_client
from discordbot.messages import format_message
from discordbot.version import get_app_version

APP_VERSION = get_app_version()


def _configure_logging(log_level: str) -> logging.Logger:
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s.%(msecs)03d %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger(__name__)


def main() -> None:
    config = load_config()
    logger = _configure_logging(config.log_level)
    logger.info(format_message("startup", version=APP_VERSION))
    client = build_discord_client(config=config, logger=logger)
    client.run(config.discord_bot_token, log_handler=None)


if __name__ == "__main__":
    main()
