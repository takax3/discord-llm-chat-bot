MESSAGES = {
    "startup": "Starting discordbot v{version}",
    "database_ready": "SQLite initialized at {sqlite_path}",
    "discord_ready": "Discord client connected as {user}",
    "mention_received": "Received mention from user_id={user_id} channel_id={channel_id}",
    "guild_disabled": "Skipped reply because guild_id={guild_id} is disabled",
    "channel_not_allowed": "Skipped reply because channel_id={channel_id} is not allowed for guild_id={guild_id}",
    "thinking": "Thinking...",
    "ollama_fallback": "Fell back to error reply because Ollama request failed for channel_id={channel_id}",
    "reply_sent": "Sent mention reply to message_id={message_id}",
}


def format_message(message_key: str, **kwargs: object) -> str:
    template = MESSAGES[message_key]
    return template.format(**kwargs)
