from __future__ import annotations

import sqlite3
from pathlib import Path


CREATE_GUILD_SETTINGS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS guild_settings (
    guild_id INTEGER PRIMARY KEY,
    is_enabled INTEGER NOT NULL DEFAULT 1,
    allowed_channel_ids TEXT NOT NULL DEFAULT '',
    ollama_model TEXT,
    system_prompt TEXT,
    max_history_messages INTEGER,
    max_response_chars INTEGER,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""


def initialize_database(sqlite_path: Path) -> sqlite3.Connection:
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(sqlite_path)
    connection.execute(CREATE_GUILD_SETTINGS_TABLE_SQL)
    connection.commit()
    return connection
