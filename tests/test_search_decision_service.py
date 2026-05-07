from discordbot.domain.search_decision import SearchDecision
from discordbot.services.search_decision_service import _parse_search_decision


def test_parse_search_decision_returns_answer_action() -> None:
    decision = _parse_search_decision(
        '{"action":"answer","answer":"direct answer"}',
        fallback_query="query",
    )

    assert decision == SearchDecision(action="answer", answer="direct answer")


def test_parse_search_decision_returns_search_action() -> None:
    decision = _parse_search_decision(
        '{"action":"search","search_query":"latest openai news","reason":"latest"}',
        fallback_query="query",
    )

    assert decision == SearchDecision(
        action="search",
        search_query="latest openai news",
        reason="latest",
    )


def test_parse_search_decision_falls_back_to_answer_when_json_is_invalid() -> None:
    decision = _parse_search_decision(
        "plain answer",
        fallback_query="query",
    )

    assert decision == SearchDecision(action="answer", answer="plain answer")
