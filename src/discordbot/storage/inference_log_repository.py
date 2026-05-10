from __future__ import annotations

import sqlite3

from discordbot.domain.inference_log import InferenceLog


class InferenceLogRepository:
    def __init__(self, *, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def fetch_last_by_channel(self, channel_id: int) -> InferenceLog | None:
        """Return the most recent log for the given channel, or None."""
        row = self._connection.execute(
            """
            SELECT
                guild_id, channel_id, user_id, message_received_at,
                decision_started_at, decision_ended_at,
                search_started_at, search_ended_at,
                inference_started_at, inference_ended_at, reply_sent_at,
                decision_prompt_tokens, decision_completion_tokens, search_query_count,
                inference_prompt_tokens, inference_completion_tokens,
                is_error, gpu_avg_watts, gpu_energy_joules
            FROM inference_logs
            WHERE channel_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (channel_id,),
        ).fetchone()
        if row is None:
            return None
        return InferenceLog(
            guild_id=row[0],
            channel_id=row[1],
            user_id=row[2],
            message_received_at=row[3],
            decision_started_at=row[4],
            decision_ended_at=row[5],
            search_started_at=row[6],
            search_ended_at=row[7],
            inference_started_at=row[8],
            inference_ended_at=row[9],
            reply_sent_at=row[10],
            decision_prompt_tokens=row[11],
            decision_completion_tokens=row[12],
            search_query_count=row[13],
            inference_prompt_tokens=row[14],
            inference_completion_tokens=row[15],
            is_error=bool(row[16]),
            gpu_avg_watts=row[17],
            gpu_energy_joules=row[18],
        )

    def save(self, log: InferenceLog) -> None:
        self._connection.execute(
            """
            INSERT INTO inference_logs (
                guild_id,
                channel_id,
                user_id,
                message_received_at,
                decision_started_at,
                decision_ended_at,
                search_started_at,
                search_ended_at,
                inference_started_at,
                inference_ended_at,
                reply_sent_at,
                decision_prompt_tokens,
                decision_completion_tokens,
                search_query_count,
                inference_prompt_tokens,
                inference_completion_tokens,
                is_error,
                gpu_avg_watts,
                gpu_energy_joules
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                log.guild_id,
                log.channel_id,
                log.user_id,
                log.message_received_at,
                log.decision_started_at,
                log.decision_ended_at,
                log.search_started_at,
                log.search_ended_at,
                log.inference_started_at,
                log.inference_ended_at,
                log.reply_sent_at,
                log.decision_prompt_tokens,
                log.decision_completion_tokens,
                log.search_query_count,
                log.inference_prompt_tokens,
                log.inference_completion_tokens,
                1 if log.is_error else 0,
                log.gpu_avg_watts,
                log.gpu_energy_joules,
            ),
        )
        self._connection.commit()
