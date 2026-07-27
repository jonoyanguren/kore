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
