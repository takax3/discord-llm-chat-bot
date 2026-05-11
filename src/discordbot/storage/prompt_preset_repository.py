from __future__ import annotations

import sqlite3

from discordbot.domain.prompt_preset import PromptPreset


class PromptPresetRepository:
    def __init__(self, *, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def save(self, preset: PromptPreset) -> None:
        self._connection.execute(
            """
            INSERT INTO prompt_presets (guild_id, name, prompt)
            VALUES (?, ?, ?)
            ON CONFLICT(guild_id, name) DO UPDATE SET prompt = excluded.prompt
            """,
            (preset.guild_id, preset.name, preset.prompt),
        )
        self._connection.commit()

    def delete(self, *, guild_id: int, name: str) -> bool:
        cursor = self._connection.execute(
            "DELETE FROM prompt_presets WHERE guild_id = ? AND name = ?",
            (guild_id, name),
        )
        self._connection.commit()
        return cursor.rowcount > 0

    def list_presets(self, *, guild_id: int) -> list[PromptPreset]:
        rows = self._connection.execute(
            "SELECT guild_id, name, prompt FROM prompt_presets WHERE guild_id = ? ORDER BY name",
            (guild_id,),
        ).fetchall()
        return [PromptPreset(guild_id=int(r[0]), name=str(r[1]), prompt=str(r[2])) for r in rows]

    def get_by_name(self, *, guild_id: int, name: str) -> PromptPreset | None:
        row = self._connection.execute(
            "SELECT guild_id, name, prompt FROM prompt_presets WHERE guild_id = ? AND name = ?",
            (guild_id, name),
        ).fetchone()
        if row is None:
            return None
        return PromptPreset(guild_id=int(row[0]), name=str(row[1]), prompt=str(row[2]))
