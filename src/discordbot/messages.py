MESSAGES = {
    "startup": "Starting discordbot v{version}",
    "discord_ready": "Discord client connected as {user}",
    "mention_received": "Received mention from user_id={user_id} channel_id={channel_id}",
    "reply_sent": "Sent mention reply to message_id={message_id}",
}


def format_message(message_key: str, **kwargs: object) -> str:
    template = MESSAGES[message_key]
    return template.format(**kwargs)
