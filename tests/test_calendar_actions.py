"""Calendar event → task / prep helpers."""

from __future__ import annotations

from app.integrations.google_calendar.actions import _fallback_task, _event_user_block


def test_fallback_task_prefixes_prep():
    out = _fallback_task(
        {"title": "Sync Datafine", "starts_at": "2026-08-10T15:00"}
    )
    assert out["title"].startswith("Prep:")
    assert "15:00" in (out["notes"] or "")


def test_event_user_block_includes_link():
    block = _event_user_block(
        {
            "title": "1:1",
            "starts_at": "2026-08-11T10:00",
            "ends_at": "2026-08-11T10:30",
            "html_link": "https://calendar.google.com/x",
        }
    )
    assert "1:1" in block
    assert "https://calendar.google.com/x" in block
