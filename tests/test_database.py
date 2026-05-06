from pathlib import Path
from uuid import uuid4

from discordbot.storage.database import initialize_database


def test_initialize_database_creates_guild_settings_table() -> None:
    sqlite_path = Path("data") / f"test-{uuid4().hex}.db"
    connection = None

    try:
        connection = initialize_database(sqlite_path)
        row = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name = 'guild_settings'
            """
        ).fetchone()

        assert row == ("guild_settings",)
        assert sqlite_path.exists()
    finally:
        if connection is not None:
            connection.close()
        if sqlite_path.exists():
            sqlite_path.unlink()
