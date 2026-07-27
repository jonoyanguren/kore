"""Unit tests for LLM tool-argument parsing helpers."""

from __future__ import annotations

from app.llm.llm_assistant import _parse_tool_arguments, _tool_calls_for_history


def test_parse_tool_arguments_ok():
    assert _parse_tool_arguments('{"a": 1}') == {"a": 1}
    assert _parse_tool_arguments(None) == {}


def test_parse_tool_arguments_truncated():
    # Truncated mid-string — repair should close quote/brace or return None
    got = _parse_tool_arguments('{"champion": "Ahri", "note": "hello')
    assert got is None or isinstance(got, dict)


def test_tool_calls_for_history_skips_null_function():
    class TC:
        id = "1"
        function = None

    assert _tool_calls_for_history([TC()]) == []


def test_tool_calls_for_history_ok():
    class Fn:
        name = "web_search"
        arguments = '{"query": "x"}'

    class TC:
        id = "c1"
        function = Fn()

    assert _tool_calls_for_history([TC()]) == [
        {
            "id": "c1",
            "type": "function",
            "function": {"name": "web_search", "arguments": '{"query": "x"}'},
        }
    ]


def test_wants_strong_model():
    from app.llm.llm_assistant import wants_strong_model

    assert not wants_strong_model("hola qué tal")
    assert wants_strong_model("haz un coaching para subir en soloQ")
    assert wants_strong_model("x" * 401)


def test_resolve_model_strong():
    from app.config import settings
    from app.llm.llm_assistant import resolve_model

    prev = settings.openrouter_model
    prev_s = settings.openrouter_model_strong
    try:
        settings.openrouter_model = "anthropic/claude-sonnet-4.6"
        settings.openrouter_model_strong = "anthropic/claude-opus-4.8"
        assert resolve_model(strong=False) == "anthropic/claude-sonnet-4.6"
        assert resolve_model(strong=True) == "anthropic/claude-opus-4.8"
    finally:
        settings.openrouter_model = prev
        settings.openrouter_model_strong = prev_s
