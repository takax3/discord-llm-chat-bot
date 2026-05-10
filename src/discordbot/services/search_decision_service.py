from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from discordbot.domain.conversation_message import ConversationMessage
from discordbot.domain.search_decision import SearchDecision
from discordbot.integrations.ollama_client import OllamaClient, OllamaClientError


class SearchDecisionService:
    def __init__(self, *, ollama_client: OllamaClient) -> None:
        self._ollama_client = ollama_client

    async def decide(
        self,
        *,
        prior_messages: list[ConversationMessage],
        user_message: str,
        user_images: list[str] | None = None,
    ) -> SearchDecision:
        """メインモデルが1回の呼び出しで検索要否とクエリ（複数可）を判定する。"""
        images = user_images or []
        messages = self._build_decision_messages(
            prior_messages=prior_messages,
            user_message=user_message,
            user_images=images,
        )
        try:
            result = await self._ollama_client.generate_reply(messages)
        except OllamaClientError:
            return SearchDecision(action="answer")
        decision = _parse_search_decision(result.content, fallback_query=user_message)
        return SearchDecision(
            action=decision.action,
            search_queries=decision.search_queries,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
        )

    def _build_decision_messages(
        self,
        *,
        prior_messages: list[ConversationMessage],
        user_message: str,
        user_images: list[str],
    ) -> list[dict[str, object]]:
        now = datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M JST")
        # プロンプト設計: 判定とクエリ生成を1回で完結させる（速度優先）。
        # 検索が必要な場合は search_queries に日本語キーワードを1件以上列挙する。
        # 複数の独立した知識が必要なとき（例: 複数人物・複数トピック）は複数クエリを列挙する。
        # 不確かな場合は検索に倒す（ハルシネーション防止）。
        # 出力: {"action":"search","search_queries":["q1","q2",...]} or {"action":"answer"}
        #        fence（```json）はモデルが付けがちなため JSON のみを指示する。
        messages: list[dict[str, object]] = [
            {
                "role": "system",
                "content": (
                    f"You are a search routing assistant. Today is {now}. "
                    'If search is needed, return {"action":"search","search_queries":["<Japanese keywords>", ...]}. '
                    "You may include multiple queries when the question requires independent pieces of knowledge "
                    "(e.g. different people, different topics). "
                    'Otherwise return {"action":"answer"}. '
                    "JSON only, no markdown fences. "
                    "Search when: the topic involves recent events, politics, laws, regulations, rapidly changing information, "
                    "niche or specialized knowledge such as games, anime, manga, hobbies, or specific community topics, "
                    "or when your knowledge may be missing or outdated. Search conditions take priority. "
                    "If you are uncertain or do not know the answer, prefer search over answer. "
                    "Do not search when: the task requires only reasoning with no external knowledge needed — math, coding, translation, or logical inference."
                ),
            }
        ]
        for message in prior_messages:
            messages.append({"role": message.role, "content": message.content})
        user_entry: dict[str, object] = {"role": "user", "content": user_message}
        if user_images:
            user_entry["images"] = user_images
        messages.append(user_entry)
        return messages


def _parse_search_decision(raw_content: str, *, fallback_query: str) -> SearchDecision:
    """判定とクエリを同時に含む JSON レスポンスをパースする。"""
    stripped = raw_content.strip()
    normalized = stripped.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        payload = json.loads(normalized)
    except json.JSONDecodeError:
        return SearchDecision(action="answer")
    action = str(payload.get("action", "")).strip().lower()
    if action != "search":
        return SearchDecision(action="answer")

    # search_queries 配列（新形式）を優先、search_query 単一フィールド（後方互換）もサポート。
    raw_queries = payload.get("search_queries")
    if isinstance(raw_queries, list):
        queries = tuple(str(q).strip() for q in raw_queries if str(q).strip())
    else:
        single = str(payload.get("search_query", "")).strip()
        queries = (single,) if single else ()

    if not queries:
        queries = (fallback_query,)
    return SearchDecision(action="search", search_queries=queries)
