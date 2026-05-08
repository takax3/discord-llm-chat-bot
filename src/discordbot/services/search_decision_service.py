from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
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
        on_pending: Callable[[str], Awaitable[None]] | None = None,
        on_result: Callable[[str], Awaitable[None]] | None = None,
    ) -> SearchDecision:
        # Step 1: ジャンルラベルを生成する。
        # 後続の判定（Step 3 の明示的検索確認、Step 4 の変動性判定）に渡すコンテキストとして使う。
        if on_pending:
            await on_pending("ジャンルを推論中……")
        genre = await self._classify_genre(
            prior_messages=prior_messages,
            user_message=user_message,
        )
        if genre is None:
            return SearchDecision(action="answer")
        if on_result:
            await on_result(f"ジャンル: {genre}")

        # Step 2: ユーザーが何を知りたいかを1文で要約する。
        # prior_messages は渡さず user_message のみを使う（コンテキスト拡張を最小化）。
        # 生成した要約を Step 3 の明示的検索判定と Step 5 のクエリ生成に渡す。
        if on_pending:
            await on_pending("クエリ概要を推論中……")
        query_summary = await self._summarize_query(user_message=user_message)
        if on_result and query_summary:
            summary_short = query_summary[:60] + ("..." if len(query_summary) > 60 else "")
            await on_result(f"クエリ概要: {summary_short}")

        # Step 3: ユーザーが明示的に検索・調査を要求しているかを判定する。
        # ジャンルとクエリ概要をコンテキストとして渡すことで判定精度を上げる。
        if on_pending:
            await on_pending("検索要求を推論中……")
        is_explicit = await self._is_explicit_search_request(
            prior_messages=prior_messages,
            user_message=user_message,
            genre=genre,
            query_summary=query_summary,
        )
        if on_result:
            await on_result(f"明示的な検索要求: {'あり' if is_explicit else 'なし'}")

        # Step 3 が true なら Step 4（変動性判定）をスキップして直接クエリ生成へ。
        if not is_explicit:
            # Step 4: ジャンルが最新情報・変動が激しい領域かどうかを判定する。
            if on_pending:
                await on_pending("変動性を推論中……")
            needs_fresh = await self._needs_fresh_info(
                topic_summary=genre,
                user_message=user_message,
            )
            if on_result:
                await on_result(f"最新情報が必要: {'あり' if needs_fresh else 'なし'}")
            if not needs_fresh:
                return SearchDecision(action="answer")

        # Step 5: query_summary を活用して精度の高い検索クエリを生成する。
        if on_pending:
            await on_pending("検索クエリを生成中……")
        search_query = await self._generate_query(
            prior_messages=prior_messages,
            user_message=user_message,
            fallback=user_message,
            topic_summary=query_summary,
        )
        if on_result:
            await on_result(f"検索クエリ: {search_query}")
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
        # プロンプト設計: ルーターなし構成用。判定とクエリ生成を1回で完結させる。
        # 高性能モデルであれば両タスクを同時に処理できるため、ルーターあり構成のような多段分割は不要（速度優先）。
        # 検索する条件は _needs_fresh_info・_is_explicit_search_request と同じ軸で統一する。
        # 不確かな場合は検索に倒す（ハルシネーション防止）。
        # 出力: {"action":"search","search_query":"日本語 キーワード"} または {"action":"answer"}
        #        fence（```json）はモデルが付けがちなため JSON のみを指示する。
        messages: list[dict[str, object]] = [
            {
                "role": "system",
                "content": (
                    f"You are a search routing assistant. Today is {now}. "
                    'If search is needed, return {"action":"search","search_query":"<Japanese keywords separated by spaces>"}. '
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

    async def _is_explicit_search_request(
        self,
        *,
        prior_messages: list[ConversationMessage],
        user_message: str,
        genre: str | None = None,
        query_summary: str | None = None,
    ) -> bool:
        """ユーザーが明示的に検索・調査を求めているかを判定する。失敗時は False を返す。"""
        # プロンプト設計: 「調べて」「検索して」「探して」等の明示的な検索指示のみ true とする。
        # 暗黙的な知識要求（「〜ってどうなの？」等）は false に倒す。
        # タスクを「表層的な意図読み取り」に絞ることで 1B モデルでも安定する。
        # ジャンルとクエリ概要をユーザーターンに付加し、文脈からの判定精度を上げる。
        # 出力: {"result": true/false}
        # 失敗フォールバック: false（チェーンを継続）
        messages: list[dict[str, object]] = [
            {
                "role": "system",
                "content": (
                    "Your task is to classify the user's intent, not to answer the question. "
                    'Return {"result":true} if the user is explicitly asking to search, '
                    "look up, investigate, or find information. "
                    'Return {"result":false} for everything else. '
                    "JSON only, no markdown fences."
                ),
            }
        ]
        for message in prior_messages:
            messages.append({"role": message.role, "content": message.content})
        context_lines: list[str] = []
        if genre:
            context_lines.append(f"Genre: {genre}")
        if query_summary:
            context_lines.append(f"Summary: {query_summary}")
        user_content = "\n".join(context_lines) + f"\n\nMessage: {user_message}" if context_lines else user_message
        messages.append({"role": "user", "content": user_content})

        try:
            result = await self._ollama_client.generate_reply(messages)
        except OllamaClientError:
            return False
        return _parse_bool_result(result.content, fallback=False)

    async def _classify_genre(
        self,
        *,
        prior_messages: list[ConversationMessage],
        user_message: str,
    ) -> str | None:
        """クエリのジャンルを短いラベルで返す。失敗・空文字時は None を返す。"""
        # プロンプト設計: クエリのジャンルを短い日本語ラベルで出力させる。
        # タスクを「ラベル付け」に絞ることで小モデルが回答を生成するのを防ぐ。
        # 具体的なジャンル例で出力フォーマットを固定し、分類不能な場合は「不明」を許容する。
        # 出力: 日本語の短いジャンルラベル（例: 政治・時事）または 不明
        # 失敗フォールバック: None（decide() が answer に倒す）
        messages: list[dict[str, object]] = [
            {
                "role": "system",
                "content": (
                    "Output a short genre label in Japanese for the user's question "
                    "(e.g. 政治・時事, ゲーム, プログラミング, アニメ・マンガ, スポーツ, 科学). "
                    "If the genre is unclear, output '不明'. "
                    "Do NOT answer the question. "
                    "Output only the genre label, no explanation."
                ),
            }
        ]
        for message in prior_messages:
            messages.append({"role": message.role, "content": message.content})
        messages.append({"role": "user", "content": user_message})

        try:
            result = await self._ollama_client.generate_reply(messages)
        except OllamaClientError:
            return None
        genre = result.content.strip().split("\n")[0]
        return genre if genre else None

    async def _summarize_query(
        self,
        *,
        user_message: str,
    ) -> str | None:
        """ユーザーのクエリを1文に要約する。失敗・空文字時は None を返す。"""
        # プロンプト設計: ユーザーのクエリを1文に要約させる（回答させない）。
        # タスクを「クエリの要約」に絞ることで、モデルが答えを生成するのを防ぐ。
        # prior_messages は渡さず user_message のみを入力とし、コンテキスト拡張を最小化する。
        # 出力: 日本語1文の検索意図（例: 現在の日本の首相の名前を知りたい）
        # 失敗フォールバック: None（_generate_query が user_message にフォールバック）
        messages: list[dict[str, object]] = [
            {
                "role": "system",
                "content": (
                    "Your task is to summarize the user's query, not to answer it. "
                    "Summarize the user's query in one sentence in Japanese. "
                    "Output only the summarized query, nothing else."
                ),
            }
        ]
        messages.append({"role": "user", "content": user_message})

        try:
            result = await self._ollama_client.generate_reply(messages)
        except OllamaClientError:
            return None
        summary = result.content.strip()
        return summary if summary else None

    async def _needs_fresh_info(
        self,
        *,
        topic_summary: str,
        user_message: str,
    ) -> bool:
        """トピックが最新情報・変動が激しい領域かどうかを判定する。失敗時は True を返す。"""
        # プロンプト設計: トピックが変動しやすい領域か安定した知識かをカテゴリ分類させる。
        # 「このタイプのトピックは変動するか」という分類タスクに絞ることで、
        # モデル自身の知識の鮮度評価（「自分は知っているか」）と混同させない。
        # 日時注入不要: 現在日時ではなくトピックの性質で判断させるため。
        # ユーザーターンには genre（ジャンルラベル）+ 元メッセージを渡す。prior_messages は不要。
        # 出力: {"result": true/false}
        # 失敗フォールバック: true（不確かなら検索に倒す）
        messages: list[dict[str, object]] = [
            {
                "role": "system",
                "content": (
                    "Your task is to classify the topic type, not to answer the question. "
                    'Return {"result":true} if the topic requires current, frequently-changing, '
                    "or recently-released information (news, prices, standings, schedules, new releases, "
                    "recent events, current laws or regulations, game updates, entertainment releases). "
                    'Return {"result":false} if the topic is stable knowledge that does not change '
                    "(history, science concepts, math, language, classic literature, established technology). "
                    "JSON only, no markdown fences."
                ),
            },
            {
                "role": "user",
                "content": f"Topic: {topic_summary}\n\nQuestion: {user_message}",
            },
        ]

        try:
            result = await self._ollama_client.generate_reply(messages)
        except OllamaClientError:
            return True
        return _parse_bool_result(result.content, fallback=True)

    async def _generate_query(
        self,
        *,
        prior_messages: list[ConversationMessage],
        user_message: str,
        fallback: str,
        topic_summary: str | None = None,
    ) -> str:
        """検索クエリを日本語スペース区切りで生成する。失敗・空文字時は fallback を返す。"""
        # プロンプト設計: 検索エンジンに渡す日本語キーワード列のみを生成させる。
        # 要否判定はせず「キーワード生成」タスクに絞ることで小モデルでも安定する。
        # 英語変換は 1B モデルでは不安定なため日本語のまま生成させる。
        # 説明文・句読点・記号を禁止してキーワード列のみを返させる。
        # topic_summary（クエリ概要）がある場合はユーザーターンに付加して生成精度を上げる。
        # 出力: 日本語キーワードのスペース区切り列（例: 現在 内閣総理大臣 名前）
        # 失敗フォールバック: fallback（通常は user_message）
        messages: list[dict[str, object]] = [
            {
                "role": "system",
                "content": (
                    "Your task is to generate a search query, not to answer the question. "
                    "Generate a concise Japanese search query for the user's request. "
                    "Output keywords only, separated by spaces. "
                    "Do not include explanations, punctuation, or extra text."
                ),
            }
        ]
        for message in prior_messages:
            messages.append({"role": message.role, "content": message.content})

        if topic_summary:
            user_content = f"Topic context: {topic_summary}\n\nRequest: {user_message}"
        else:
            user_content = user_message

        messages.append({"role": "user", "content": user_content})

        try:
            result = await self._ollama_client.generate_reply(messages)
        except OllamaClientError:
            return fallback
        query = result.content.strip()
        return query or fallback


def _parse_bool_result(raw_content: str, *, fallback: bool) -> bool:
    """{"result": true/false} 形式の JSON をパースする。_is_explicit_search_request と _needs_fresh_info で共用。"""
    stripped = raw_content.strip()
    normalized = stripped.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        payload = json.loads(normalized)
    except json.JSONDecodeError:
        return fallback
    result = payload.get("result")
    if isinstance(result, bool):
        return result
    return fallback


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
