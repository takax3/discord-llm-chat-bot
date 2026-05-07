from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


SearchAction = Literal["answer", "search"]


@dataclass(frozen=True)
class SearchDecision:
    action: SearchAction
    answer: str = ""
    search_query: str = ""
    reason: str = ""
