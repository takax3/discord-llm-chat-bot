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
        images = user_images or []

        # 第1段階: 検索の要否のみを判定する。
        # 小モデルに「判断」と「クエリ生成」を同時にさせると精度が落ちるため分離。
        action = await self._decide_action(
            prior_messages=prior_messages,
            user_message=user_message,
            user_images=images,
        )
        if action != "search":
            return SearchDecision(action="answer")

        # 第2段階: 検索が必要と判定された場合のみ、検索クエリを生成する。
        search_query = await self._generate_query(
            prior_messages=prior_messages,
            user_message=user_message,
            user_images=images,
            fallback=user_message,
        )
        return SearchDecision(action="search", search_query=search_query)

    async def decide_combined(
        self,
        *,
        prior_messages: list[ConversationMessage],
        user_message: str,
        user_images: list[str] | None = None,
    ) -> SearchDecision:
        """メインモデル用。判定とクエリ生成を1回の呼び出しで行う（速度優先）。"""
        images = user_images or []
        messages = self._build_combined_messages(
            prior_messages=prior_messages,
            user_message=user_message,
            user_images=images,
        )
        try:
            result = await self._ollama_client.generate_reply(messages)
        except OllamaClientError:
            return SearchDecision(action="answer")
        return _parse_search_decision(result.content, fallback_query=user_message)

    def _build_combined_messages(
        self,
        *,
        prior_messages: list[ConversationMessage],
        user_message: str,
        user_images: list[str],
    ) -> list[dict[str, object]]:
        now = datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M JST")
        messages: list[dict[str, object]] = [
            {
                "role": "system",
                # メインモデル用: 判定とクエリ生成を1回にまとめる。
                # 高性能モデルであれば両タスクを同時に処理できるため分離不要。
                # 検索条件は _decide_action と同じ軸で統一する。
                "content": (
                    f"You are a search routing assistant. Today is {now}. "
                    # 検索が必要なら action と search_query を同時に返す。1回の呼び出しで完結させる。
                    # search_query は日本語キーワードをスペース区切りで生成させる。
                    'If search is needed, return {"action":"search","search_query":"<Japanese keywords separated by spaces>"}. '
                    # 検索不要なら action のみ。余分なフィールドを防ぐ。
                    'Otherwise return {"action":"answer"}. '
                    # JSON のみを返させる。fence（```json）はモデルが付けがちなため禁止。
                    "JSON only, no markdown fences. "
                    # 検索する条件: _decide_action と同じ軸で統一。最新性・変動性・知識欠如・ニッチ専門知識。
                    "Search when: the topic involves recent events, politics, laws, regulations, rapidly changing information, "
                    # ニッチ・専門知識: ゲーム・アニメ・マンガ・特定コミュニティなど深い専門知識が必要な領域。
                    "niche or specialized knowledge such as games, anime, manga, hobbies, or specific community topics, "
                    "or when your knowledge may be missing or outdated. Search conditions take priority. "
                    # 知識がない・不確かなら諦めず検索に倒す。ハルシネーション防止。
                    "If you are uncertain or do not know the answer, prefer search over answer. "
                    # 検索しない条件: 外部知識ゼロの純粋推論タスク（計算・コード・翻訳・論理推論）。
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

    async def _decide_action(
        self,
        *,
        prior_messages: list[ConversationMessage],
        user_message: str,
        user_images: list[str],
    ) -> str:
        now = datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M JST")
        messages: list[dict[str, object]] = [
            {
                "role": "system",
                # 役割: 検索要否の二択判定のみ。タスクを絞ることで小モデル（1B）でも安定させる。
                # 検索する: 最新情報・政治・時事・法律・変動が激しい領域、または知識が欠如・陳腐化している場合。
                # 検索しない: 計算・コード・翻訳・文章生成・論理推論など外部知識が不要な純粋推論タスク。
                # 返し方: {"action":"search"} または {"action":"answer"} の JSON のみ（fence 禁止）。
                "content": (
                    f"You are a search routing assistant. Today is {now}. "
                    'Return {"action":"search"} or {"action":"answer"} as JSON only, no markdown fences. '
                    "Search when: the topic involves recent events, politics, laws, regulations, rapidly changing information, "
                    # ニッチ・専門知識: ゲーム・アニメ・マンガ・特定コミュニティなど深い専門知識が必要な領域。
                    # ファンが持つコアな知識（キャラクター詳細・攻略・設定等）はモデルの網羅率が低いため検索優先。
                    "niche or specialized knowledge such as games, anime, manga, hobbies, or specific community topics, "
                    "or when your knowledge may be missing or outdated. Search conditions take priority. "
                    # 純粋推論タスク（外部知識ゼロ）のみ answer に倒す。
                    # writing は調査まとめ等で検索が必要なケースがあるため除外。
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

        try:
            result = await self._ollama_client.generate_reply(messages)
        except OllamaClientError:
            return "answer"
        return _parse_action(result.content)

    async def _generate_query(
        self,
        *,
        prior_messages: list[ConversationMessage],
        user_message: str,
        user_images: list[str],
        fallback: str,
    ) -> str:
        messages: list[dict[str, object]] = [
            {
                "role": "system",
                "content": (
                    # 役割: 検索クエリ生成のみ。要否判定はしない。
                    "You are a search query generator for a web search engine. "
                    # 日本語キーワードをスペース区切りで返す。
                    # 英語変換は小モデルでは不安定なため日本語のまま生成させる。
                    "Generate a concise Japanese search query for the user's request. "
                    "Output keywords only, separated by spaces. "
                    # 説明文・句読点・記号は不要。検索エンジンに渡すキーワード列のみ。
                    "Do not include explanations, punctuation, or extra text."
                ),
            }
        ]
        for message in prior_messages:
            messages.append({"role": message.role, "content": message.content})
        user_entry: dict[str, object] = {"role": "user", "content": user_message}
        if user_images:
            user_entry["images"] = user_images
        messages.append(user_entry)

        try:
            result = await self._ollama_client.generate_reply(messages)
        except OllamaClientError:
            return fallback
        query = result.content.strip()
        return query or fallback


def _parse_action(raw_content: str) -> str:
    stripped = raw_content.strip()
    normalized = stripped.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        payload = json.loads(normalized)
    except json.JSONDecodeError:
        return "answer"
    action = str(payload.get("action", "")).strip().lower()
    return action if action in ("search", "answer") else "answer"


def _parse_search_decision(raw_content: str, *, fallback_query: str) -> SearchDecision:
    """判定とクエリを同時に含む JSON レスポンスをパースする。"""
    stripped = raw_content.strip()
    normalized = stripped.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        payload = json.loads(normalized)
    except json.JSONDecodeError:
        return SearchDecision(action="answer")
    action = str(payload.get("action", "")).strip().lower()
    if action == "search":
        query = str(payload.get("search_query", "")).strip() or fallback_query
        return SearchDecision(action="search", search_query=query)
    return SearchDecision(action="answer")
