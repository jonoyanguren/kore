"""Unit tests for OpenRouter usage snapshot helpers."""

from __future__ import annotations

import app.llm.openrouter_credits as mod
from app.llm.openrouter_credits import (
    UsageSnapshot,
    _merge,
    _pct,
    snapshot_from_credits,
    snapshot_from_key,
)


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


def test_credits_wallet_remaining():
    s = snapshot_from_credits({"total_credits": 100.5, "total_usage": 25.75})
    assert s is not None
    assert s.remaining_usd == 74.75
    assert s.source == "credits"


def test_key_limit_remaining():
    s = snapshot_from_key(
        {
            "usage": 10.0,
            "usage_monthly": 1.5,
            "limit": 20.0,
            "limit_remaining": 9.5,
            "limit_reset": "monthly",
        }
    )
    assert s is not None
    assert s.remaining_usd == 9.5
    assert s.total_usd == 20.0
    assert s.pct_used == 52.5
    assert s.usage_usd == 10.0
    assert s.usage_monthly_usd == 1.5
    assert s.unlimited is False


def test_key_without_limit_is_unlimited():
    s = snapshot_from_key({"usage": 3.0, "usage_monthly": 0.4})
    assert s is not None
    assert s.unlimited is True
    assert s.remaining_usd is None
    d = s.as_dict()
    assert d["remaining_usd"] is None
    assert d["usage_monthly_usd"] == 0.4


def test_merge_prefers_credits_wallet():
    credits = snapshot_from_credits({"total_credits": 50.0, "total_usage": 10.0})
    key = snapshot_from_key(
        {"usage": 99.0, "usage_monthly": 2.0, "limit": 5.0, "limit_remaining": 1.0}
    )
    merged = _merge(credits, key)
    assert merged is not None
    assert merged.remaining_usd == 40.0
    assert merged.source == "credits"
    assert merged.usage_monthly_usd == 2.0


def test_cache_reset_for_isolation():
    mod._cache = None
