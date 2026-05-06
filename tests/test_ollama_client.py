import asyncio

from discordbot.integrations.ollama_client import build_ollama_payload
from discordbot.integrations.ollama_client import OllamaClient


def test_build_ollama_payload_uses_single_turn_messages() -> None:
    payload = build_ollama_payload(
        model="qwen3:8b",
        messages=[
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "hello"},
        ],
    )

    assert payload["model"] == "qwen3:8b"
    assert payload["stream"] is False
    assert payload["messages"] == [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "hello"},
    ]


def test_prewarm_uses_single_user_prompt(monkeypatch) -> None:
    captured: dict[str, object] = {}
    client = OllamaClient(
        base_url="http://ollama:11434",
        model="gemma4:26b",
        system_prompt="system",
        timeout_seconds=60,
    )

    def fake_request(messages):
        captured["messages"] = messages
        return "ok"

    monkeypatch.setattr(OllamaClient, "_request_chat_sync", lambda self, messages: fake_request(messages))

    asyncio.run(client.prewarm("warm up"))

    assert captured["messages"] == [{"role": "user", "content": "warm up"}]
