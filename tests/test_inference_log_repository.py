import sqlite3

import pytest

from discordbot.domain.inference_log import InferenceLog
from discordbot.storage.database import CREATE_INFERENCE_LOGS_TABLE_SQL
from discordbot.storage.inference_log_repository import InferenceLogRepository


@pytest.fixture
def connection():
    conn = sqlite3.connect(":memory:")
    conn.execute(CREATE_INFERENCE_LOGS_TABLE_SQL)
    conn.commit()
    yield conn
    conn.close()


def _make_log(**overrides) -> InferenceLog:
    defaults = dict(
        guild_id=111,
        channel_id=222,
        user_id=333,
        message_received_at="2026-05-09T12:00:00.000Z",
        decision_started_at="2026-05-09T12:00:00.010Z",
        decision_ended_at="2026-05-09T12:00:00.500Z",
        search_started_at="2026-05-09T12:00:00.510Z",
        search_ended_at="2026-05-09T12:00:01.000Z",
        inference_started_at="2026-05-09T12:00:01.010Z",
        inference_ended_at="2026-05-09T12:00:05.000Z",
        reply_sent_at="2026-05-09T12:00:05.050Z",
        decision_prompt_tokens=512,
        decision_completion_tokens=30,
        search_query_count=2,
        inference_prompt_tokens=1024,
        inference_completion_tokens=200,
        is_error=False,
        gpu_avg_watts=280.5,
        gpu_energy_joules=1402.5,
    )
    defaults.update(overrides)
    return InferenceLog(**defaults)


def test_save_inserts_record(connection) -> None:
    repo = InferenceLogRepository(connection=connection)
    repo.save(_make_log())

    row = connection.execute("SELECT COUNT(*) FROM inference_logs").fetchone()
    assert row[0] == 1


def test_save_stores_all_fields(connection) -> None:
    repo = InferenceLogRepository(connection=connection)
    log = _make_log()
    repo.save(log)

    row = connection.execute(
        "SELECT guild_id, channel_id, user_id, message_received_at, "
        "decision_started_at, decision_ended_at, "
        "search_started_at, search_ended_at, "
        "inference_started_at, inference_ended_at, reply_sent_at, "
        "decision_prompt_tokens, decision_completion_tokens, search_query_count, "
        "inference_prompt_tokens, inference_completion_tokens, is_error "
        "FROM inference_logs"
    ).fetchone()

    assert row[0] == 111
    assert row[1] == 222
    assert row[2] == 333
    assert row[3] == "2026-05-09T12:00:00.000Z"
    assert row[11] == 512
    assert row[12] == 30
    assert row[13] == 2
    assert row[14] == 1024
    assert row[15] == 200
    assert row[16] == 0


def test_save_stores_null_timestamps_when_search_not_used(connection) -> None:
    repo = InferenceLogRepository(connection=connection)
    log = _make_log(
        decision_started_at=None,
        decision_ended_at=None,
        search_started_at=None,
        search_ended_at=None,
        search_query_count=0,
    )
    repo.save(log)

    row = connection.execute(
        "SELECT decision_started_at, decision_ended_at, search_started_at, search_ended_at, search_query_count "
        "FROM inference_logs"
    ).fetchone()

    assert row[0] is None
    assert row[1] is None
    assert row[2] is None
    assert row[3] is None
    assert row[4] == 0


def test_save_stores_null_tokens_when_error(connection) -> None:
    repo = InferenceLogRepository(connection=connection)
    log = _make_log(
        inference_started_at="2026-05-09T12:00:01.010Z",
        inference_ended_at=None,
        reply_sent_at=None,
        inference_prompt_tokens=None,
        inference_completion_tokens=None,
        is_error=True,
    )
    repo.save(log)

    row = connection.execute(
        "SELECT inference_prompt_tokens, inference_completion_tokens, is_error "
        "FROM inference_logs"
    ).fetchone()

    assert row[0] is None
    assert row[1] is None
    assert row[2] == 1


def test_save_multiple_records(connection) -> None:
    repo = InferenceLogRepository(connection=connection)
    repo.save(_make_log(user_id=1))
    repo.save(_make_log(user_id=2))
    repo.save(_make_log(user_id=3))

    count = connection.execute("SELECT COUNT(*) FROM inference_logs").fetchone()[0]
    assert count == 3


def test_fetch_last_by_channel_returns_none_when_empty(connection) -> None:
    repo = InferenceLogRepository(connection=connection)
    assert repo.fetch_last_by_channel(channel_id=222) is None


def test_fetch_last_by_channel_returns_most_recent(connection) -> None:
    repo = InferenceLogRepository(connection=connection)
    repo.save(_make_log(user_id=1))
    repo.save(_make_log(user_id=2))

    result = repo.fetch_last_by_channel(channel_id=222)
    assert result is not None
    assert result.user_id == 2


def test_fetch_last_by_channel_ignores_other_channels(connection) -> None:
    repo = InferenceLogRepository(connection=connection)
    repo.save(_make_log(channel_id=111, user_id=10))
    repo.save(_make_log(channel_id=999, user_id=20))

    result = repo.fetch_last_by_channel(channel_id=111)
    assert result is not None
    assert result.user_id == 10
    assert result.channel_id == 111


def test_fetch_last_by_channel_maps_all_fields(connection) -> None:
    repo = InferenceLogRepository(connection=connection)
    log = _make_log()
    repo.save(log)

    result = repo.fetch_last_by_channel(channel_id=222)
    assert result is not None
    assert result.guild_id == log.guild_id
    assert result.decision_prompt_tokens == log.decision_prompt_tokens
    assert result.decision_completion_tokens == log.decision_completion_tokens
    assert result.search_query_count == log.search_query_count
    assert result.inference_prompt_tokens == log.inference_prompt_tokens
    assert result.inference_completion_tokens == log.inference_completion_tokens
    assert result.is_error == log.is_error
    assert result.decision_started_at == log.decision_started_at
    assert result.inference_ended_at == log.inference_ended_at
