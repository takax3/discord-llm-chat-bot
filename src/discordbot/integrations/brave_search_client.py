from __future__ import annotations

import asyncio
import gzip
import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from discordbot.domain.search_result import SearchResult


class BraveSearchClientError(RuntimeError):
    pass


@dataclass(frozen=True)
class BraveSearchClient:
    api_key: str
    max_results: int
    timeout_seconds: int
    country: str
    language: str

    async def search(self, query: str) -> list[SearchResult]:
        return await asyncio.to_thread(self._search_sync, query)

    def _search_sync(self, query: str) -> list[SearchResult]:
        params = urllib.parse.urlencode(
            {
                "q": query,
                "count": str(self.max_results),
                "country": self.country,
                "search_lang": self.language,
            }
        )
        search_request = urllib.request.Request(
            url=f"https://api.search.brave.com/res/v1/web/search?{params}",
            headers={
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": self.api_key,
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(
                search_request,
                timeout=self.timeout_seconds,
            ) as response:
                raw_body = response.read()
                if response.headers.get("Content-Encoding", "").lower() == "gzip":
                    raw_body = gzip.decompress(raw_body)
                payload = json.loads(raw_body.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            logger = logging.getLogger(__name__)
            response_body = _read_http_error_body(exc)
            logger.warning(
                "Brave Search API request failed status=%s reason=%s body=%s",
                exc.code,
                exc.reason,
                response_body,
            )
            raise BraveSearchClientError("Failed to call Brave Search API.") from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise BraveSearchClientError("Failed to call Brave Search API.") from exc

        web = payload.get("web", {})
        results = web.get("results", [])
        if not isinstance(results, list):
            return []

        normalized_results: list[SearchResult] = []
        for result in results[: self.max_results]:
            if not isinstance(result, dict):
                continue
            title = str(result.get("title", "")).strip()
            url = str(result.get("url", "")).strip()
            snippet = str(result.get("description") or result.get("snippet") or "").strip()
            if not snippet:
                extra_snippets = result.get("extra_snippets")
                if isinstance(extra_snippets, list) and extra_snippets:
                    snippet = str(extra_snippets[0]).strip()
            if not title or not url:
                continue
            normalized_results.append(
                SearchResult(
                    title=title,
                    url=url,
                    snippet=snippet,
                )
            )
        return normalized_results


def _read_http_error_body(error: urllib.error.HTTPError) -> str:
    if error.fp is None:
        return ""
    try:
        raw_body = error.read()
    except OSError:
        return ""
    if not raw_body:
        return ""
    if error.headers.get("Content-Encoding", "").lower() == "gzip":
        try:
            raw_body = gzip.decompress(raw_body)
        except OSError:
            return ""
    return raw_body.decode("utf-8", errors="replace").strip()
