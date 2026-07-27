"""Unit tests for OpenRouter usage snapshot helpers."""

from __future__ import annotations

import app.llm.openrouter_credits as mod
from app.llm.openrouter_credits import UsageSnapshot, _pct


def test_pct_bounds():
    assert _pct(0, 10) == 0.0
    assert _pct(5, 10) == 50.0
    assert _pct(12, 10) == 100.0
    assert _pct(1, 0) == 0.0


def test_usage_snapshot_dict():
    s = UsageSnapshot(usage_usd=1.008, total_usd=5.0, pct_used=20.16, source="credits")
    d = s.as_dict()
    assert d["usage_usd"] == 1.008
    assert d["total_usd"] == 5.0
    assert d["remaining_usd"] == 3.992
    assert d["pct_used"] == 20.2
    assert d["source"] == "credits"


def test_cache_reset_for_isolation():
    mod._cache = None
