MESSAGES = {
    "startup": "Starting discordbot v{version}",
    "database_ready": "SQLite initialized at {sqlite_path}",
    "ollama_prewarm_started": "Starting Ollama prewarm for model={model}",
    "ollama_prewarm_completed": "Completed Ollama prewarm for model={model}",
    "ollama_prewarm_failed": "Ollama prewarm failed for model={model}",
    "discord_ready": "Discord client connected as {user}",
    "mention_received": "Received mention from user_id={user_id} channel_id={channel_id}",
    "reply_context_received": "Received reply-context message from user_id={user_id} channel_id={channel_id} reference_message_id={reference_message_id}",
    "guild_disabled": "Skipped reply because guild_id={guild_id} is disabled",
    "channel_not_allowed": "Skipped reply because channel_id={channel_id} is not allowed for guild_id={guild_id}",
    "thinking": "Thinking... (Queue ahead: {queue_ahead})",
    "ollama_fallback": "Fell back to error reply because Ollama request failed for channel_id={channel_id}",
    "conversation_message_saved": "Saved conversation message discord_message_id={message_id} role={role}",
    "reply_sent": "Sent mention reply to message_id={message_id}",
    "shutdown_requested": "Received {signal_name}, scheduling graceful shutdown",
    "shutdown_started": "Graceful shutdown started signal_name={signal_name}",
    "presence_offline": "Presence set to offline",
    "presence_offline_failed": "Failed to set presence offline during shutdown",
    "signal_handler_not_supported": "Signal handlers are not supported for {signal_name} on this platform",
}


def format_message(message_key: str, **kwargs: object) -> str:
    template = MESSAGES[message_key]
    return template.format(**kwargs)
