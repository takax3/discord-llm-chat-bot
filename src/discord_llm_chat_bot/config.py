from __future__ import annotations

import os
from dataclasses import dataclass

from discord_llm_chat_bot.constants import DEFAULT_LOG_LEVEL


@dataclass(frozen=True)
class AppConfig:
    log_level: str


def load_config() -> AppConfig:
    return AppConfig(
        log_level=os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper(),
    )
