from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InferenceLog:
    guild_id: int
    channel_id: int
    user_id: int
    message_received_at: str
    decision_started_at: str | None
    decision_ended_at: str | None
    search_started_at: str | None
    search_ended_at: str | None
    inference_started_at: str | None
    inference_ended_at: str | None
    reply_sent_at: str | None
    decision_prompt_tokens: int | None
    decision_completion_tokens: int | None
    search_query_count: int
    inference_prompt_tokens: int | None
    inference_completion_tokens: int | None
    is_error: bool
    gpu_avg_watts: float | None
    gpu_energy_joules: float | None
