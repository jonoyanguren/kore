"""OpenRouter account spend for the console chip (USD + %)."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

OPENROUTER_CREDITS_URL = "https://openrouter.ai/api/v1/credits"
OPENROUTER_KEY_URL = "https://openrouter.ai/api/v1/key"
_CACHE_TTL_S = 60.0

_cache: tuple[float, "UsageSnapshot"] | None = None


@dataclass(frozen=True)
class UsageSnapshot:
    """Spend vs purchased (or key limit). Amounts in USD."""

    usage_usd: float
    total_usd: float
    pct_used: float
    source: str  # "credits" | "key"

    def as_dict(self) -> dict[str, Any]:
        return {
            "usage_usd": round(self.usage_usd, 4),
            "total_usd": round(self.total_usd, 4),
            "remaining_usd": round(max(self.total_usd - self.usage_usd, 0.0), 4),
            "pct_used": round(self.pct_used, 1),
            "source": self.source,
        }


def _pct(usage: float, total: float) -> float:
    if total <= 0:
        return 0.0
    return min(100.0, max(0.0, (usage / total) * 100.0))


async def _fetch_credits(client: httpx.AsyncClient, api_key: str) -> UsageSnapshot | None:
    r = await client.get(
        OPENROUTER_CREDITS_URL,
        headers={"Authorization": f"Bearer {api_key}"},
    )
    if r.status_code == 403:
        return None
    r.raise_for_status()
    data = (r.json() or {}).get("data") or {}
    total = float(data.get("total_credits") or 0)
    usage = float(data.get("total_usage") or 0)
    if total <= 0 and usage <= 0:
        return None
    # If only usage is known, still show USD; % needs a total.
    if total <= 0:
        return None
    return UsageSnapshot(
        usage_usd=usage,
        total_usd=total,
        pct_used=_pct(usage, total),
        source="credits",
    )


async def _fetch_key(client: httpx.AsyncClient, api_key: str) -> UsageSnapshot | None:
    r = await client.get(
        OPENROUTER_KEY_URL,
        headers={"Authorization": f"Bearer {api_key}"},
    )
    r.raise_for_status()
    data = (r.json() or {}).get("data") or {}
    usage = float(data.get("usage") or data.get("usage_monthly") or 0)
    limit = data.get("limit")
    budget = settings.openrouter_budget_usd
    total: float | None = None
    if limit is not None:
        total = float(limit)
    elif budget > 0:
        total = float(budget)
    if total is None or total <= 0:
        return None
    return UsageSnapshot(
        usage_usd=usage,
        total_usd=total,
        pct_used=_pct(usage, total),
        source="key",
    )


async def fetch_usage(*, force: bool = False) -> UsageSnapshot | None:
    """Return cached OpenRouter spend, or None if unavailable."""
    global _cache
    now = time.monotonic()
    if not force and _cache is not None and now - _cache[0] < _CACHE_TTL_S:
        return _cache[1]

    api_key = (settings.openrouter_api_key or "").strip()
    if not api_key:
        return None

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            snap = await _fetch_credits(client, api_key)
            if snap is None:
                snap = await _fetch_key(client, api_key)
    except Exception:
        logger.exception("OpenRouter usage fetch failed")
        return _cache[1] if _cache else None

    if snap is not None:
        _cache = (now, snap)
    return snap
