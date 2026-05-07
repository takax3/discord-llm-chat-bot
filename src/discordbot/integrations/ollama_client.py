from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from discordbot.config import AppConfig


class OllamaClientError(RuntimeError):
    pass


@dataclass(frozen=True)
class OllamaChatResult:
    content: str
    tokens_per_second: float | None


@dataclass(frozen=True)
class OllamaClient:
    base_url: str
    model: str
    system_prompt: str
    timeout_seconds: int

    @classmethod
    def from_config(cls, config: AppConfig) -> "OllamaClient":
        return cls(
            base_url=config.ollama_base_url.rstrip("/"),
            model=config.ollama_model,
            system_prompt=config.system_prompt,
            timeout_seconds=config.ollama_timeout_seconds,
        )

    async def generate_reply(self, messages: list[dict[str, object]]) -> OllamaChatResult:
        return await asyncio.to_thread(self._request_chat_sync, messages)

    async def prewarm(self, prompt: str) -> None:
        messages: list[dict[str, object]] = [{"role": "user", "content": prompt}]
        await asyncio.to_thread(self._request_chat_sync, messages)

    def _request_chat_sync(self, messages: list[dict[str, object]]) -> OllamaChatResult:
        payload = build_ollama_payload(
            model=self.model,
            messages=messages,
        )
        ollama_request = urllib.request.Request(
            url=f"{self.base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                ollama_request,
                timeout=self.timeout_seconds,
            ) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise OllamaClientError("Failed to call Ollama.") from exc

        message = response_payload.get("message", {})
        content = str(message.get("content", "")).strip()
        if not content:
            raise OllamaClientError("Ollama returned an empty response.")
        return OllamaChatResult(
            content=content,
            tokens_per_second=_extract_tokens_per_second(response_payload),
        )


def build_ollama_payload(
    *,
    model: str,
    messages: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "model": model,
        "stream": False,
        "messages": messages,
    }


def _extract_tokens_per_second(response_payload: dict[str, object]) -> float | None:
    eval_count = response_payload.get("eval_count")
    eval_duration = response_payload.get("eval_duration")
    if not isinstance(eval_count, int) or not isinstance(eval_duration, int):
        return None
    if eval_count <= 0 or eval_duration <= 0:
        return None
    duration_seconds = eval_duration / 1_000_000_000
    if duration_seconds <= 0:
        return None
    return eval_count / duration_seconds
