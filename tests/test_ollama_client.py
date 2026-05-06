from discordbot.integrations.ollama_client import build_ollama_payload


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
