from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PromptPreset:
    guild_id: int
    name: str
    prompt: str
