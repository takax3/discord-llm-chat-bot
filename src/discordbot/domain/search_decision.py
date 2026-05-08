from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


SearchAction = Literal["answer", "search"]


@dataclass(frozen=True)
class SearchDecision:
    action: SearchAction
    search_queries: tuple[str, ...] = field(default_factory=tuple)
