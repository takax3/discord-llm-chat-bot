import logging

from discord_llm_chat_bot.config import load_config
from discord_llm_chat_bot.messages import format_message
from discord_llm_chat_bot.version import get_app_version

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


if __name__ == "__main__":
    main()
