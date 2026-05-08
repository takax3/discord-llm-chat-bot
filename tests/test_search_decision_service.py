from discordbot.domain.search_decision import SearchDecision
from discordbot.services.search_decision_service import _parse_search_decision


def test_parse_search_decision_returns_answer_action() -> None:
    decision = _parse_search_decision(
        '{"action":"answer"}',
        fallback_query="query",
    )

    assert decision == SearchDecision(action="answer")


def test_parse_search_decision_returns_search_action() -> None:
    decision = _parse_search_decision(
        '{"action":"search","search_query":"latest openai news"}',
        fallback_query="query",
    )

    assert decision == SearchDecision(action="search", search_query="latest openai news")


def test_parse_search_decision_falls_back_to_answer_when_json_is_invalid() -> None:
    decision = _parse_search_decision(
        "plain answer",
        fallback_query="query",
    )

    assert decision == SearchDecision(action="answer")


def test_parse_search_decision_uses_fallback_query_when_search_query_is_empty() -> None:
    decision = _parse_search_decision(
        '{"action":"search","search_query":""}',
        fallback_query="fallback",
    )

    assert decision == SearchDecision(action="search", search_query="fallback")
