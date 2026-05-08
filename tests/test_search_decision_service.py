from discordbot.domain.search_decision import SearchDecision
from discordbot.services.search_decision_service import _parse_search_decision


def test_parse_search_decision_returns_answer_action() -> None:
    decision = _parse_search_decision(
        '{"action":"answer"}',
        fallback_query="query",
    )

    assert decision == SearchDecision(action="answer")


def test_parse_search_decision_returns_search_action_with_queries_array() -> None:
    decision = _parse_search_decision(
        '{"action":"search","search_queries":["latest openai news","openai gpt5"]}',
        fallback_query="query",
    )

    assert decision == SearchDecision(
        action="search", search_queries=("latest openai news", "openai gpt5")
    )


def test_parse_search_decision_returns_search_action_with_single_query() -> None:
    decision = _parse_search_decision(
        '{"action":"search","search_queries":["latest openai news"]}',
        fallback_query="query",
    )

    assert decision == SearchDecision(action="search", search_queries=("latest openai news",))


def test_parse_search_decision_falls_back_to_answer_when_json_is_invalid() -> None:
    decision = _parse_search_decision(
        "plain answer",
        fallback_query="query",
    )

    assert decision == SearchDecision(action="answer")


def test_parse_search_decision_uses_fallback_query_when_search_queries_is_empty() -> None:
    decision = _parse_search_decision(
        '{"action":"search","search_queries":[]}',
        fallback_query="fallback",
    )

    assert decision == SearchDecision(action="search", search_queries=("fallback",))


def test_parse_search_decision_accepts_legacy_search_query_field() -> None:
    decision = _parse_search_decision(
        '{"action":"search","search_query":"legacy query"}',
        fallback_query="fallback",
    )

    assert decision == SearchDecision(action="search", search_queries=("legacy query",))


def test_parse_search_decision_strips_markdown_fences() -> None:
    decision = _parse_search_decision(
        '```json\n{"action":"search","search_queries":["q1"]}\n```',
        fallback_query="fallback",
    )

    assert decision == SearchDecision(action="search", search_queries=("q1",))
