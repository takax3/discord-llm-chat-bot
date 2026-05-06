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

    async def generate_reply(self, user_message: str) -> str:
        return await asyncio.to_thread(self._generate_reply_sync, user_message)

    def _generate_reply_sync(self, user_message: str) -> str:
        payload = build_ollama_payload(
            model=self.model,
            system_prompt=self.system_prompt,
            user_message=user_message,
        )
        request = urllib.request.Request(
            url=f"{self.base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise OllamaClientError("Failed to call Ollama.") from exc

        message = response_payload.get("message", {})
        content = str(message.get("content", "")).strip()
        if not content:
            raise OllamaClientError("Ollama returned an empty response.")
        return content


def build_ollama_payload(
    *,
    model: str,
    system_prompt: str,
    user_message: str,
) -> dict[str, object]:
    return {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    }
