import asyncio
import io
import json
import logging
from urllib.error import HTTPError, URLError

from discordbot.webhook_logging import (
    WEBHOOK_COLOR_ERROR,
    WEBHOOK_COLOR_SUCCESS,
    WEBHOOK_EVENT_SHUTDOWN,
    WEBHOOK_EVENT_STARTUP,
    WEBHOOK_USER_AGENT,
    DiscordWebhookNotifier,
    should_send_webhook,
)


def make_record(
    level: int,
    *,
    webhook_event: str | None = None,
    skip_webhook: bool = False,
) -> logging.LogRecord:
    record = logging.LogRecord(
        name="discordbot.test",
        level=level,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )
    if webhook_event is not None:
        record.webhook_event = webhook_event
    if skip_webhook:
        record.skip_webhook = True
    return record


def test_should_send_webhook_allows_startup_event() -> None:
    record = make_record(logging.INFO, webhook_event=WEBHOOK_EVENT_STARTUP)

    assert should_send_webhook(
        record,
        notify_startup=True,
        notify_shutdown=False,
        notify_logs=False,
        minimum_level=logging.ERROR,
    )


def test_should_send_webhook_allows_shutdown_event() -> None:
    record = make_record(logging.INFO, webhook_event=WEBHOOK_EVENT_SHUTDOWN)

    assert should_send_webhook(
        record,
        notify_startup=False,
        notify_shutdown=True,
        notify_logs=False,
        minimum_level=logging.ERROR,
    )


def test_should_send_webhook_uses_minimum_level_for_regular_logs() -> None:
    assert not should_send_webhook(
        make_record(logging.WARNING),
        notify_startup=False,
        notify_shutdown=False,
        notify_logs=True,
        minimum_level=logging.ERROR,
    )
    assert should_send_webhook(
        make_record(logging.ERROR),
        notify_startup=False,
        notify_shutdown=False,
        notify_logs=True,
        minimum_level=logging.ERROR,
    )


def test_send_startup_started_posts_embed_payload(monkeypatch) -> None:
    sent: list[dict[str, object]] = []
    notifier = DiscordWebhookNotifier(
        webhook_urls=("https://example.com/webhook",),
        minimum_level_name="ERROR",
        notify_startup=True,
        notify_shutdown=True,
        notify_logs=False,
    )

    def fake_post(self, url: str, payload: dict[str, object]) -> None:
        sent.append(payload)

    monkeypatch.setattr(DiscordWebhookNotifier, "_post_payload", fake_post)

    asyncio.run(notifier.send_startup_started(version="1.0.0", model="gemma4:26b"))

    embed = sent[0]["embeds"][0]
    assert embed["title"] == "Bot Startup Started"
    assert {"name": "Model", "value": "gemma4:26b", "inline": True} in embed["fields"]


def test_send_ready_posts_embed_payload(monkeypatch) -> None:
    sent: list[dict[str, object]] = []
    notifier = DiscordWebhookNotifier(
        webhook_urls=("https://example.com/webhook",),
        minimum_level_name="ERROR",
        notify_startup=True,
        notify_shutdown=True,
        notify_logs=False,
    )

    def fake_post(self, url: str, payload: dict[str, object]) -> None:
        sent.append(payload)

    monkeypatch.setattr(DiscordWebhookNotifier, "_post_payload", fake_post)

    asyncio.run(notifier.send_ready(version="1.0.0", guild_count=2, model="gemma4:26b"))

    embed = sent[0]["embeds"][0]
    assert embed["title"] == "Bot Ready"
    assert embed["color"] == WEBHOOK_COLOR_SUCCESS
    assert {"name": "Version", "value": "1.0.0", "inline": True} in embed["fields"]
    assert {"name": "Guilds", "value": "2", "inline": True} in embed["fields"]


def test_build_record_payload_uses_embed_for_regular_logs() -> None:
    notifier = DiscordWebhookNotifier(
        webhook_urls=("https://example.com/webhook",),
        minimum_level_name="ERROR",
        notify_startup=True,
        notify_shutdown=True,
        notify_logs=True,
    )

    payload = notifier._build_record_payload(make_record(logging.ERROR))

    embed = payload["embeds"][0]
    assert embed["title"] == "Bot Log: ERROR"
    assert embed["color"] == WEBHOOK_COLOR_ERROR
    assert embed["description"] == "hello"


def test_post_payload_logs_http_status_details(monkeypatch, caplog) -> None:
    notifier = DiscordWebhookNotifier(
        webhook_urls=("https://example.com/webhook",),
        minimum_level_name="ERROR",
        notify_startup=True,
        notify_shutdown=True,
        notify_logs=False,
    )

    def fake_urlopen(*args, **kwargs):
        request_object = args[0]
        assert request_object.headers["User-agent"] == WEBHOOK_USER_AGENT
        assert request_object.headers["Accept"] == "application/json"
        request_payload = json.loads(request_object.data.decode("utf-8"))
        assert "embeds" in request_payload
        raise HTTPError(
            url="https://example.com/webhook",
            code=403,
            msg="Forbidden",
            hdrs=None,
            fp=io.BytesIO(b'{"message":"Missing Access","code":50013}'),
        )

    monkeypatch.setattr("discordbot.webhook_logging.request.urlopen", fake_urlopen)

    with caplog.at_level(logging.WARNING):
        notifier._post_payload("https://example.com/webhook", {"embeds": [{"title": "hello"}]})

    assert "status=403" in caplog.text
    assert "Forbidden" in caplog.text
    assert "Missing Access" in caplog.text


def test_post_payload_logs_urlerror_reason(monkeypatch, caplog) -> None:
    notifier = DiscordWebhookNotifier(
        webhook_urls=("https://example.com/webhook",),
        minimum_level_name="ERROR",
        notify_startup=True,
        notify_shutdown=True,
        notify_logs=False,
    )

    def fake_urlopen(*args, **kwargs):
        raise URLError("timeout")

    monkeypatch.setattr("discordbot.webhook_logging.request.urlopen", fake_urlopen)

    with caplog.at_level(logging.WARNING):
        notifier._post_payload("https://example.com/webhook", {"embeds": [{"title": "hello"}]})

    assert "reason=timeout" in caplog.text
