"""Tests for OpenRouter prompt-cache helpers."""

from __future__ import annotations

from app.llm.prompt_cache import (
    needs_explicit_cache,
    openrouter_extra_body,
    with_system_cache_control,
)


def test_needs_explicit_cache():
    assert needs_explicit_cache("anthropic/claude-haiku-4.5")
    assert needs_explicit_cache("qwen/qwen3-max")
    assert not needs_explicit_cache("deepseek/deepseek-v4-pro")
    assert not needs_explicit_cache("moonshotai/kimi-k2.5")


def test_with_system_cache_control_anthropic():
    msgs = [
        {"role": "system", "content": "You are Jone."},
        {"role": "user", "content": "hola"},
    ]
    out = with_system_cache_control(msgs, model="anthropic/claude-haiku-4.5")
    assert out[0]["role"] == "system"
    assert isinstance(out[0]["content"], list)
    assert out[0]["content"][0]["cache_control"] == {"type": "ephemeral"}
    assert out[1]["content"] == "hola"


def test_with_system_cache_control_deepseek_noop():
    msgs = [{"role": "system", "content": "sys"}, {"role": "user", "content": "u"}]
    out = with_system_cache_control(msgs, model="deepseek/deepseek-v4-pro")
    assert out == msgs


def test_openrouter_extra_body():
    deep = openrouter_extra_body(model="deepseek/deepseek-v4-pro", session_id="m-1")
    assert deep == {"session_id": "m-1"}
    anth = openrouter_extra_body(model="anthropic/claude-haiku-4.5", session_id="d-1")
    assert anth["session_id"] == "d-1"
    assert anth["cache_control"] == {"type": "ephemeral"}
