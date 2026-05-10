from __future__ import annotations

import discord


class PresenceService:
    def __init__(self, *, model: str = "") -> None:
        self._model = model
        self._queue_count = 0
        self._tokens_per_second: float | None = None

    def set_queue_count(self, queue_count: int) -> None:
        self._queue_count = max(queue_count, 0)

    def set_tokens_per_second(self, tokens_per_second: float | None) -> None:
        self._tokens_per_second = tokens_per_second

    def build_status_text(self) -> str:
        speed_text = "-- tok/s"
        if self._tokens_per_second is not None:
            speed_text = f"{self._tokens_per_second:.1f} tok/s"
        model_text = f"{self._model} | " if self._model else ""
        return f"{model_text}Queue: {self._queue_count} | {speed_text}"

    def build_activity(self) -> discord.BaseActivity:
        return discord.Game(name=self.build_status_text())
