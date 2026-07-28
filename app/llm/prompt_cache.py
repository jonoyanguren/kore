"""OpenRouter prompt caching helpers (Anthropic explicit + sticky session).

DeepSeek / Moonshot / Gemini: automatic cache — we only pin `session_id`.
Anthropic / Qwen: need `cache_control` (top-level automatic + system breakpoint).
"""

from __future__ import annotations

from typing import Any


def needs_explicit_cache(model: str) -> bool:
    m = (model or "").strip().lower()
    return m.startswith("anthropic/") or m.startswith("qwen/")


def with_system_cache_control(
    messages: list[dict[str, Any]],
    *,
    model: str,
) -> list[dict[str, Any]]:
    """Mark the system message for Anthropic/Qwen explicit cache breakpoints."""
    if not needs_explicit_cache(model):
        return messages

    out: list[dict[str, Any]] = []
    for msg in messages:
        if msg.get("role") != "system":
            out.append(msg)
            continue
        content = msg.get("content")
        cache = {"type": "ephemeral"}
        if isinstance(content, str):
            out.append(
                {
                    **msg,
                    "content": [
                        {"type": "text", "text": content, "cache_control": cache}
                    ],
                }
            )
            continue
        if isinstance(content, list) and content:
            parts = [dict(p) if isinstance(p, dict) else p for p in content]
            last_text_i = None
            for i, part in enumerate(parts):
                if isinstance(part, dict) and part.get("type") == "text":
                    last_text_i = i
            if last_text_i is not None:
                parts[last_text_i] = {**parts[last_text_i], "cache_control": cache}
            out.append({**msg, "content": parts})
            continue
        out.append(msg)
    return out


def openrouter_extra_body(
    *,
    model: str,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Fields for OpenAI SDK `extra_body` (session sticky + Anthropic auto-cache)."""
    body: dict[str, Any] = {}
    sid = (session_id or "").strip()
    if sid:
        body["session_id"] = sid[:256]
    if needs_explicit_cache(model):
        # Automatic breakpoint advances as the tool-loop history grows.
        body["cache_control"] = {"type": "ephemeral"}
    return body
