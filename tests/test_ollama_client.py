import asyncio

from discordbot.integrations.ollama_client import build_ollama_payload
from discordbot.integrations.ollama_client import OllamaChatResult, OllamaClient


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
        return OllamaChatResult(content="ok", tokens_per_second=None)

    monkeypatch.setattr(OllamaClient, "_request_chat_sync", lambda self, messages: fake_request(messages))

    asyncio.run(client.prewarm("warm up"))

    assert captured["messages"] == [{"role": "user", "content": "warm up"}]


def test_generate_reply_returns_tokens_per_second(monkeypatch) -> None:
    client = OllamaClient(
        base_url="http://ollama:11434",
        model="qwen3.6:27b",
        system_prompt="system",
        timeout_seconds=60,
    )

    monkeypatch.setattr(
        OllamaClient,
        "_request_chat_sync",
        lambda self, messages: OllamaChatResult(
            content="hello",
            tokens_per_second=12.5,
        ),
    )

    result = asyncio.run(client.generate_reply([{"role": "user", "content": "hi"}]))

    assert result.content == "hello"
    assert result.tokens_per_second == 12.5
