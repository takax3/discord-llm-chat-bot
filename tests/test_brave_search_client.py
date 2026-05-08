import json
import io
from urllib.error import HTTPError, URLError

import pytest

from discordbot.integrations.brave_search_client import (
    BraveSearchClient,
    BraveSearchClientError,
)


def test_search_parses_web_results(monkeypatch: pytest.MonkeyPatch) -> None:
    client = BraveSearchClient(
        api_key="brave-key",
        max_results=3,
        timeout_seconds=10,
        country="JP",
        language="ja",
    )

    class FakeResponse:
        headers = {}

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def read(self) -> bytes:
            return json.dumps(
                {
                    "web": {
                        "results": [
                            {
                                "title": "Title",
                                "url": "https://example.com",
                                "description": "Snippet",
                            }
                        ]
                    }
                }
            ).encode("utf-8")

    monkeypatch.setattr(
        "discordbot.integrations.brave_search_client.urllib.request.urlopen",
        lambda *args, **kwargs: FakeResponse(),
    )

    results = client._search_sync("query")

    assert len(results) == 1
    assert results[0].title == "Title"
    assert results[0].url == "https://example.com"
    assert results[0].snippet == "Snippet"
    assert results[0].extra_snippets == ()
    assert results[0].age == ""


def test_search_parses_extra_snippets_and_age(monkeypatch: pytest.MonkeyPatch) -> None:
    client = BraveSearchClient(
        api_key="brave-key",
        max_results=3,
        timeout_seconds=10,
        country="JP",
        language="ja",
    )

    class FakeResponse:
        headers = {}

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def read(self) -> bytes:
            return json.dumps(
                {
                    "web": {
                        "results": [
                            {
                                "title": "Title",
                                "url": "https://example.com",
                                "description": "Main snippet",
                                "extra_snippets": ["Extra 1", "Extra 2"],
                                "age": "2 days ago",
                            }
                        ]
                    }
                }
            ).encode("utf-8")

    monkeypatch.setattr(
        "discordbot.integrations.brave_search_client.urllib.request.urlopen",
        lambda *args, **kwargs: FakeResponse(),
    )

    results = client._search_sync("query")

    assert results[0].snippet == "Main snippet"
    assert results[0].extra_snippets == ("Extra 1", "Extra 2")
    assert results[0].age == "2 days ago"


def test_search_parses_gzip_response(monkeypatch: pytest.MonkeyPatch) -> None:
    client = BraveSearchClient(
        api_key="brave-key",
        max_results=3,
        timeout_seconds=10,
        country="JP",
        language="ja",
    )

    class FakeResponse:
        headers = {"Content-Encoding": "gzip"}

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def read(self) -> bytes:
            import gzip

            return gzip.compress(
                json.dumps(
                    {
                        "web": {
                            "results": [
                                {
                                    "title": "Title",
                                    "url": "https://example.com",
                                    "description": "Snippet",
                                }
                            ]
                        }
                    }
                ).encode("utf-8")
            )

    monkeypatch.setattr(
        "discordbot.integrations.brave_search_client.urllib.request.urlopen",
        lambda *args, **kwargs: FakeResponse(),
    )

    results = client._search_sync("query")

    assert len(results) == 1


def test_search_raises_when_request_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    client = BraveSearchClient(
        api_key="brave-key",
        max_results=3,
        timeout_seconds=10,
        country="JP",
        language="ja",
    )

    monkeypatch.setattr(
        "discordbot.integrations.brave_search_client.urllib.request.urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(URLError("timeout")),
    )

    with pytest.raises(BraveSearchClientError):
        client._search_sync("query")


def test_search_logs_http_error_details(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    client = BraveSearchClient(
        api_key="brave-key",
        max_results=3,
        timeout_seconds=10,
        country="JP",
        language="jp",
    )

    def fake_urlopen(*args, **kwargs):
        import gzip

        raise HTTPError(
            url="https://api.search.brave.com/res/v1/web/search",
            code=422,
            msg="Unprocessable Entity",
            hdrs={"Content-Encoding": "gzip"},
            fp=io.BytesIO(gzip.compress(b'{"error":"validation"}')),
        )

    monkeypatch.setattr(
        "discordbot.integrations.brave_search_client.urllib.request.urlopen",
        fake_urlopen,
    )

    with caplog.at_level("WARNING"), pytest.raises(BraveSearchClientError):
        client._search_sync("query")

    assert "status=422" in caplog.text
    assert "Unprocessable Entity" in caplog.text
    assert "validation" in caplog.text
