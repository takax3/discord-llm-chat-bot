from __future__ import annotations

import sqlite3

from discordbot.config import AppConfig
from discordbot.constants import DEFAULT_GUILD_ENABLED
from discordbot.domain.guild_settings import GuildSettings


class SettingsRepository:
    def __init__(
        self,
        *,
        connection: sqlite3.Connection,
        config: AppConfig,
    ) -> None:
        self._connection = connection
        self._config = config

    def get_guild_settings(self, guild_id: int) -> GuildSettings:
        row = self._connection.execute(
            """
            SELECT guild_id, is_enabled, allowed_channel_ids
            FROM guild_settings
            WHERE guild_id = ?
            """,
            (guild_id,),
        ).fetchone()
        if row is None:
            return GuildSettings(
                guild_id=guild_id,
                is_enabled=DEFAULT_GUILD_ENABLED,
                allowed_channel_ids=self._config.default_allowed_channel_ids,
            )

        return GuildSettings(
            guild_id=int(row[0]),
            is_enabled=bool(row[1]),
            allowed_channel_ids=_parse_channel_ids(row[2]),
        )


def _parse_channel_ids(raw_value: str) -> tuple[int, ...]:
    if not raw_value.strip():
        return ()
    return tuple(
        int(part.strip())
        for part in raw_value.split(",")
        if part.strip()
    )
