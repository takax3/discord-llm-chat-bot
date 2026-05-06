MESSAGES = {
    "startup": "Starting discordbot v{version}",
}


def format_message(message_key: str, **kwargs: object) -> str:
    template = MESSAGES[message_key]
    return template.format(**kwargs)
