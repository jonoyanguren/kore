"""Follow-up Q&A on a mission report."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from app.kernel.mission_ask import (
    clip_mission_report,
    parse_ask_events,
    ask_mission,
)


def test_clip_mission_report_short():
    assert clip_mission_report("hola") == "hola"


def test_clip_mission_report_truncates():
    blob = "x" * 50
    out = clip_mission_report(blob, max_chars=20)
    assert len(out) == 20
    assert out.endswith("…")


def test_parse_ask_events_skips_noise():
    rows = [
        ("created", "launch:normal"),
        ("ask", '{"q": "¿Cuál?", "a": "Esta"}'),
        ("ask", "not-json"),
        ("done", "tasks=2"),
    ]
    asks = parse_ask_events(rows)
    assert asks == [{"q": "¿Cuál?", "a": "Esta"}]


async def _ask_with_mock() -> str:
    msg = MagicMock()
    msg.content = "La opción A: más cerca del mar."
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    llm = AsyncMock()
    llm.chat.completions.create = AsyncMock(return_value=resp)
    return await ask_mission(
        llm,
        title="Casas",
        markdown="## Resultado\n\nElige A.\n",
        question="¿Cuál elijo?",
        history=[],
        quality="normal",
        mission_id=7,
        spend_store=None,
    )


def test_ask_mission_returns_model_text():
    import asyncio

    text = asyncio.run(_ask_with_mock())
    assert "opción A" in text.lower() or "A" in text
