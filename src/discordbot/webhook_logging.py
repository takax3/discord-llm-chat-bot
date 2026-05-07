from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib import request
from urllib.error import HTTPError, URLError

from discordbot.constants import WEBHOOK_TIMEOUT_SECONDS
from discordbot.version import get_app_version

WEBHOOK_EVENT_STARTUP = "startup"
WEBHOOK_EVENT_SHUTDOWN = "shutdown"
WEBHOOK_USER_AGENT = f"discordbot/{get_app_version()}"
WEBHOOK_DESCRIPTION_LIMIT = 4000
WEBHOOK_FIELD_LIMIT = 1000
WEBHOOK_COLOR_INFO = 0x5865F2
WEBHOOK_COLOR_SUCCESS = 0x57F287
WEBHOOK_COLOR_WARNING = 0xFEE75C
WEBHOOK_COLOR_ERROR = 0xED4245


def parse_log_level_name(level_name: str) -> int:
    return getattr(logging, level_name.upper(), logging.ERROR)


def should_send_webhook(
    record: logging.LogRecord,
    *,
    notify_startup: bool,
    notify_shutdown: bool,
    notify_logs: bool,
    minimum_level: int,
) -> bool:
    if getattr(record, "skip_webhook", False):
        return False

    webhook_event = getattr(record, "webhook_event", None)
    if webhook_event == WEBHOOK_EVENT_STARTUP:
        return notify_startup
    if webhook_event == WEBHOOK_EVENT_SHUTDOWN:
        return notify_shutdown
    if not notify_logs:
        return False
    return record.levelno >= minimum_level


@dataclass(frozen=True)
class DiscordWebhookNotifier:
    webhook_urls: tuple[str, ...]
    minimum_level_name: str
    notify_startup: bool
    notify_shutdown: bool
    notify_logs: bool

    async def send_record(self, record: logging.LogRecord) -> None:
        if not self.webhook_urls:
            return
        if not should_send_webhook(
            record,
            notify_startup=self.notify_startup,
            notify_shutdown=self.notify_shutdown,
            notify_logs=self.notify_logs,
            minimum_level=parse_log_level_name(self.minimum_level_name),
        ):
            return

        payload = self._build_record_payload(record)
        await self._post_to_all(payload)

    async def send_startup(self, *, version: str, guild_count: int) -> None:
        if not self.webhook_urls or not self.notify_startup:
            return
        payload = self._build_embed_payload(
            title="Bot Started",
            description=f"discordbot v{version} started.",
            color=WEBHOOK_COLOR_SUCCESS,
            fields=[
                {"name": "Version", "value": version, "inline": True},
                {"name": "Guilds", "value": str(guild_count), "inline": True},
            ],
        )
        await self._post_to_all(payload)

    async def send_startup_started(self, *, version: str, model: str) -> None:
        if not self.webhook_urls or not self.notify_startup:
            return
        payload = self._build_embed_payload(
            title="Bot Startup Started",
            description=f"discordbot v{version} startup processing has started.",
            color=WEBHOOK_COLOR_INFO,
            fields=[
                {"name": "Version", "value": version, "inline": True},
                {"name": "Model", "value": model, "inline": True},
            ],
        )
        await self._post_to_all(payload)

    async def send_ready(self, *, version: str, guild_count: int, model: str) -> None:
        if not self.webhook_urls or not self.notify_startup:
            return
        payload = self._build_embed_payload(
            title="Bot Ready",
            description="Warmup completed and discordbot is ready to accept chat.",
            color=WEBHOOK_COLOR_SUCCESS,
            fields=[
                {"name": "Version", "value": version, "inline": True},
                {"name": "Model", "value": model, "inline": True},
                {"name": "Guilds", "value": str(guild_count), "inline": True},
            ],
        )
        await self._post_to_all(payload)

    async def send_shutdown(self, *, signal_name: str, guild_count: int) -> None:
        if not self.webhook_urls or not self.notify_shutdown:
            return
        payload = self._build_embed_payload(
            title="Bot Shutdown Started",
            description="Graceful shutdown has started.",
            color=WEBHOOK_COLOR_WARNING,
            fields=[
                {"name": "Signal", "value": signal_name, "inline": True},
                {"name": "Guilds", "value": str(guild_count), "inline": True},
            ],
        )
        await self._post_to_all(payload)

    async def close(self) -> None:
        return None

    def _build_record_payload(self, record: logging.LogRecord) -> dict[str, object]:
        webhook_event = getattr(record, "webhook_event", None)
        if webhook_event == WEBHOOK_EVENT_STARTUP:
            return self._build_embed_payload(
                title="Bot Started",
                description=record.getMessage(),
                color=WEBHOOK_COLOR_SUCCESS,
                fields=[],
                record=record,
            )
        if webhook_event == WEBHOOK_EVENT_SHUTDOWN:
            return self._build_embed_payload(
                title="Bot Shutdown Started",
                description=record.getMessage(),
                color=WEBHOOK_COLOR_WARNING,
                fields=[],
                record=record,
            )

        return self._build_embed_payload(
            title=f"Bot Log: {record.levelname}",
            description=record.getMessage(),
            color=_color_for_level(record.levelno),
            fields=[
                {"name": "Logger", "value": record.name, "inline": True},
                {"name": "Level", "value": record.levelname, "inline": True},
            ],
            record=record,
        )

    def _build_embed_payload(
        self,
        *,
        title: str,
        description: str,
        color: int,
        fields: list[dict[str, object]],
        record: logging.LogRecord | None = None,
    ) -> dict[str, object]:
        if record is not None:
            ts = datetime.fromtimestamp(record.created, tz=timezone.utc)
        else:
            ts = datetime.now(timezone.utc)
        footer_text = ts.strftime("%Y-%m-%d %H:%M:%S UTC")
        embed: dict[str, object] = {
            "title": title,
            "description": _truncate_text(description, WEBHOOK_DESCRIPTION_LIMIT),
            "color": color,
            "fields": [
                {
                    "name": str(field["name"]),
                    "value": _truncate_text(str(field["value"]), WEBHOOK_FIELD_LIMIT),
                    "inline": bool(field.get("inline", False)),
                }
                for field in fields
            ],
            "footer": {"text": footer_text},
        }
        if record is not None:
            embed["timestamp"] = _format_timestamp(record.created)
        return {"embeds": [embed]}

    async def _post_to_all(self, payload: dict[str, object]) -> None:
        await asyncio.gather(
            *[asyncio.to_thread(self._post_payload, url, payload) for url in self.webhook_urls]
        )

    def _post_payload(self, url: str, payload: dict[str, object]) -> None:
        raw_payload = json.dumps(payload).encode("utf-8")
        webhook_request = request.Request(
            url,
            data=raw_payload,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": WEBHOOK_USER_AGENT,
            },
            method="POST",
        )
        try:
            with request.urlopen(
                webhook_request,
                timeout=WEBHOOK_TIMEOUT_SECONDS,
            ) as response:
                response.read()
        except HTTPError as error:
            logger = logging.getLogger(__name__)
            response_body = _read_error_body(error)
            logger.warning(
                "Failed to send Discord webhook notification status=%s reason=%s body=%s",
                error.code,
                error.reason,
                response_body,
                extra={"skip_webhook": True},
            )
        except URLError as error:
            logger = logging.getLogger(__name__)
            logger.warning(
                "Failed to send Discord webhook notification reason=%s",
                getattr(error, "reason", "unknown"),
                extra={"skip_webhook": True},
            )


class DiscordWebhookHandler(logging.Handler):
    def __init__(self, notifier: DiscordWebhookNotifier) -> None:
        super().__init__()
        self._notifier = notifier

    def emit(self, record: logging.LogRecord) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        loop.create_task(self._notifier.send_record(record))


def _truncate_text(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _color_for_level(levelno: int) -> int:
    if levelno >= logging.ERROR:
        return WEBHOOK_COLOR_ERROR
    if levelno >= logging.WARNING:
        return WEBHOOK_COLOR_WARNING
    return WEBHOOK_COLOR_INFO


def _format_timestamp(created: float) -> str:
    timestamp = datetime.fromtimestamp(created, tz=timezone.utc)
    return timestamp.isoformat().replace("+00:00", "Z")


def _read_error_body(error: HTTPError) -> str:
    if error.fp is None:
        return ""
    try:
        raw_body = error.read()
    except OSError:
        return ""
    if not raw_body:
        return ""
    return raw_body.decode("utf-8", errors="replace").strip()
