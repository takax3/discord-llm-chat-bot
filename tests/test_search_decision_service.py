from discordbot.domain.search_decision import SearchDecision
from discordbot.services.search_decision_service import _parse_bool_result, _parse_search_decision


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


def test_parse_bool_result_returns_true() -> None:
    assert _parse_bool_result('{"result":true}', fallback=False) is True


def test_parse_bool_result_returns_false() -> None:
    assert _parse_bool_result('{"result":false}', fallback=True) is False


def test_parse_bool_result_fallback_on_invalid_json() -> None:
    assert _parse_bool_result("not json", fallback=False) is False
    assert _parse_bool_result("not json", fallback=True) is True


def test_parse_bool_result_fallback_when_key_missing() -> None:
    assert _parse_bool_result('{"action":"search"}', fallback=False) is False


def test_parse_bool_result_fallback_when_result_is_string() -> None:
    assert _parse_bool_result('{"result":"true"}', fallback=False) is False


def test_parse_bool_result_fallback_when_result_is_int() -> None:
    assert _parse_bool_result('{"result":1}', fallback=False) is False


def test_parse_bool_result_strips_markdown_fences() -> None:
    assert _parse_bool_result("```json\n{\"result\":true}\n```", fallback=False) is True
