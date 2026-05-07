from __future__ import annotations

import json

from discordbot.domain.conversation_message import ConversationMessage
from discordbot.domain.search_decision import SearchDecision
from discordbot.integrations.ollama_client import OllamaClient, OllamaClientError


class SearchDecisionService:
    def __init__(
        self,
        *,
        ollama_client: OllamaClient,
        max_response_chars: int,
    ) -> None:
        self._ollama_client = ollama_client
        self._max_response_chars = max_response_chars

    async def decide(
        self,
        *,
        prior_messages: list[ConversationMessage],
        user_message: str,
        user_images: list[str] | None = None,
    ) -> SearchDecision:
        messages = self._build_messages(
            prior_messages=prior_messages,
            user_message=user_message,
            user_images=user_images or [],
        )
        try:
            result = await self._ollama_client.generate_reply(messages)
        except OllamaClientError:
            return SearchDecision(action="answer", answer="")
        return _parse_search_decision(
            result.content,
            fallback_query=user_message,
        )

    def _build_messages(
        self,
        *,
        prior_messages: list[ConversationMessage],
        user_message: str,
        user_images: list[str],
    ) -> list[dict[str, object]]:
        messages: list[dict[str, object]] = [
            {
                "role": "system",
                "content": (
                    "You are a routing assistant for a Discord chatbot. "
                    "Decide whether the bot should answer directly from its existing knowledge "
                    "or search the public web first. "
                    "Return JSON only. Do not include markdown fences. "
                    "If the request needs recent, changing, niche, or externally verifiable information, "
                    'return {"action":"search","search_query":"...","reason":"..."}. '
                    "If the request can be answered directly, "
                    f'return {{"action":"answer","answer":"..."}} and keep the answer within {self._max_response_chars} characters. '
                    "If images are attached and the request is mainly about describing the image, prefer answering directly. "
                    "Reply in Japanese unless the user explicitly asks for another language."
                ),
            }
        ]
        for message in prior_messages:
            messages.append(
                {
                    "role": message.role,
                    "content": message.content,
                }
            )
        user_entry: dict[str, object] = {
            "role": "user",
            "content": user_message,
        }
        if user_images:
            user_entry["images"] = user_images
        messages.append(user_entry)
        return messages


def _parse_search_decision(raw_content: str, *, fallback_query: str) -> SearchDecision:
    stripped = raw_content.strip()
    normalized = stripped.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        payload = json.loads(normalized)
    except json.JSONDecodeError:
        return SearchDecision(action="answer", answer=stripped)

    action = str(payload.get("action", "")).strip().lower()
    if action == "search":
        search_query = str(payload.get("search_query", "")).strip() or fallback_query
        reason = str(payload.get("reason", "")).strip()
        return SearchDecision(
            action="search",
            search_query=search_query,
            reason=reason,
        )
    answer = str(payload.get("answer", "")).strip()
    if answer:
        return SearchDecision(action="answer", answer=answer)
    return SearchDecision(action="answer", answer=stripped)
