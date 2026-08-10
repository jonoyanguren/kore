"""Tests for deterministic dream fallback + usable-dream checks."""

from __future__ import annotations

from types import SimpleNamespace

from app.kernel.dream import build_fallback_dream
from app.kernel.review_common import is_usable_dream


def test_build_fallback_dream_has_sections():
    text = build_fallback_dream(
        target="2026-08-09",
        spoken_target="el domingo",
        spoken_next="el lunes",
        open_tasks=[
            SimpleNamespace(title="Prep call", status="in_progress"),
            SimpleNamespace(title="Enviar mail", status="open"),
        ],
        agenda=[(1, "2026-08-10T10:00", "Standup", "planned")],
        calendar_block="1. 2026-08-10T11:00 — Dentista",
        inbox_block="1. de: a@b.com\n   asunto: Factura\n   snippet: x",
        chat_count=4,
        diary_count=1,
    )
    assert is_usable_dream(text)
    assert "Resumen" in text
    assert "Prep call" in text
    assert "Dentista" in text
    assert "Factura" in text
    assert "Briefing automático" in text
