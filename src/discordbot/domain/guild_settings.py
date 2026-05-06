from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GuildSettings:
    guild_id: int
    is_enabled: bool
    allowed_channel_ids: tuple[int, ...]
