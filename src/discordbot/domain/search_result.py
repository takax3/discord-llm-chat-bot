from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str
    extra_snippets: tuple[str, ...] = field(default_factory=tuple)
    age: str = ""
