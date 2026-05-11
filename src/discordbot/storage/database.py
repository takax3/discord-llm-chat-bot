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

CREATE_CONVERSATION_MESSAGES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS conversation_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discord_message_id INTEGER NOT NULL UNIQUE,
    reply_to_message_id INTEGER,
    guild_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""


CREATE_PROMPT_PRESETS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS prompt_presets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    prompt TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(guild_id, name)
)
"""


CREATE_INFERENCE_LOGS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS inference_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    message_received_at TEXT NOT NULL,
    decision_started_at TEXT,
    decision_ended_at TEXT,
    search_started_at TEXT,
    search_ended_at TEXT,
    inference_started_at TEXT,
    inference_ended_at TEXT,
    reply_sent_at TEXT,
    decision_prompt_tokens INTEGER,
    decision_completion_tokens INTEGER,
    search_query_count INTEGER NOT NULL DEFAULT 0,
    inference_prompt_tokens INTEGER,
    inference_completion_tokens INTEGER,
    is_error INTEGER NOT NULL DEFAULT 0,
    gpu_avg_watts REAL,
    gpu_energy_joules REAL
)
"""


def initialize_database(sqlite_path: Path) -> sqlite3.Connection:
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(sqlite_path)
    connection.execute(CREATE_GUILD_SETTINGS_TABLE_SQL)
    connection.execute(CREATE_CONVERSATION_MESSAGES_TABLE_SQL)
    connection.execute(CREATE_PROMPT_PRESETS_TABLE_SQL)
    connection.execute(CREATE_INFERENCE_LOGS_TABLE_SQL)
    connection.commit()
    return connection
