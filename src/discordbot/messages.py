"""ユーザー表示とログ出力に使うメッセージ定義。

起動、受信処理、presence 更新、終了処理の順にまとめて、
関連メッセージを追いやすくしている。
"""

MESSAGES = {
    # 起動と ready 到達。
    "startup": "Starting discordbot v{version}",
    "database_ready": "SQLite initialized at {sqlite_path}",
    "ollama_prewarm_started": "Starting Ollama prewarm for model={model}",
    "ollama_prewarm_completed": "Completed Ollama prewarm for model={model}",
    "ollama_prewarm_failed": "Ollama prewarm failed for model={model}",
    "discord_ready": "Discord client connected as {user}",

    # 受信メッセージ処理。
    "mention_received": "Received mention from user_id={user_id} channel_id={channel_id}",
    "reply_context_received": "Received reply-context message from user_id={user_id} channel_id={channel_id} reference_message_id={reference_message_id}",
    "guild_disabled": "Skipped reply because guild_id={guild_id} is disabled",
    "channel_not_allowed": "Skipped reply because channel_id={channel_id} is not allowed for guild_id={guild_id}",
    "thinking": "Waiting... (Queue ahead: {queue_ahead})",
    "deciding": "検索要否判定中…",
    "search_not_needed": "検索要否: 検索不要",
    "search_queries_decided": "検索要否: 検索要, 検索クエリ: {queries}",
    "searching": "検索中…",
    "search_completed": "検索完了",
    "inferring": "推論中…",
    "inferring_done": "推論完了",
    "ollama_fallback": "Fell back to error reply because Ollama request failed for channel_id={channel_id}",
    "web_search_failed": "Failed to search the web for query={query}",
    "conversation_message_saved": "Saved conversation message discord_message_id={message_id} role={role}",
    "reply_sent": "Sent mention reply to message_id={message_id}",

    # プリセットプロンプト操作。
    "preset_added": "プリセット **{name}** を登録しました。",
    "preset_updated": "プリセット **{name}** を更新しました。",
    "preset_already_exists": "プリセット **{name}** はすでに存在します。更新するには `/preset update` を使用してください。",
    "preset_deleted": "プリセット **{name}** を削除しました。",
    "preset_not_found": "プリセット **{name}** は見つかりません。",
    "preset_list_empty": "このサーバーに登録されたプリセットはありません。",
    "preset_list_header": "登録済みプリセット一覧:\n",
    "preset_anchor": "プリセット **{name}** を読み込みました。このメッセージへ返信してください。",

    # Presence / 状態更新。
    "presence_updated": "Updated presence status_text={status_text}",
    "presence_offline": "Presence set to offline",
    "presence_offline_failed": "Failed to set presence offline during shutdown",
    "presence_update_failed": "Failed to update presence",

    # 終了処理とプラットフォーム差異。
    "shutdown_requested": "Received {signal_name}, scheduling graceful shutdown",
    "shutdown_started": "Graceful shutdown started signal_name={signal_name}",
    "signal_handler_not_supported": "Signal handlers are not supported for {signal_name} on this platform",
}


def format_message(message_key: str, **kwargs: object) -> str:
    template = MESSAGES[message_key]
    return template.format(**kwargs)
