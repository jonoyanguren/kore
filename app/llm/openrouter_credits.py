"""OpenRouter account/key spend for the admin chip (USD + remaining)."""

from __future__ import annotations

import asyncio
import logging
import sys
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
    remaining_usd: float | None = None
    usage_monthly_usd: float = 0.0
    limit_reset: str | None = None
    unlimited: bool = False

    def as_dict(self) -> dict[str, Any]:
        rem = self.remaining_usd
        if rem is None and not self.unlimited and self.total_usd > 0:
            rem = max(self.total_usd - self.usage_usd, 0.0)
        remaining_pct = 100.0
        if rem is not None and self.total_usd > 0:
            remaining_pct = round(max(0.0, 100.0 - self.pct_used), 1)
        elif self.unlimited:
            remaining_pct = 100.0
        return {
            "usage_usd": round(self.usage_usd, 4),
            "total_usd": round(self.total_usd, 4),
            "remaining_usd": None if rem is None else round(max(rem, 0.0), 4),
            "usage_monthly_usd": round(self.usage_monthly_usd, 4),
            "pct_used": round(self.pct_used, 1),
            "remaining_pct": remaining_pct,
            "source": self.source,
            "unlimited": self.unlimited,
            "limit_reset": self.limit_reset,
        }


def _pct(usage: float, total: float) -> float:
    if total <= 0:
        return 0.0
    return min(100.0, max(0.0, (usage / total) * 100.0))


def _num(raw: Any) -> float | None:
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def snapshot_from_credits(data: dict[str, Any]) -> UsageSnapshot | None:
    total = float(data.get("total_credits") or 0)
    usage = float(data.get("total_usage") or 0)
    if total <= 0:
        return None
    remaining = max(total - usage, 0.0)
    return UsageSnapshot(
        usage_usd=usage,
        total_usd=total,
        remaining_usd=remaining,
        pct_used=_pct(usage, total),
        source="credits",
        unlimited=False,
    )


def snapshot_from_key(
    data: dict[str, Any], *, budget_usd: float = 0.0
) -> UsageSnapshot | None:
    usage = float(data.get("usage") or 0)
    monthly = float(data.get("usage_monthly") or 0)
    limit = _num(data.get("limit"))
    remaining = _num(data.get("limit_remaining"))
    reset = data.get("limit_reset")
    reset_s = str(reset) if reset else None

    if remaining is not None and remaining >= 0:
        if limit is not None and limit > 0:
            total = limit
            used_of_cap = max(total - remaining, 0.0)
        else:
            total = remaining
            used_of_cap = 0.0
        return UsageSnapshot(
            usage_usd=usage,
            total_usd=total,
            remaining_usd=remaining,
            pct_used=_pct(used_of_cap, total),
            source="key",
            usage_monthly_usd=monthly,
            limit_reset=reset_s,
            unlimited=False,
        )

    if limit is not None and limit > 0:
        return UsageSnapshot(
            usage_usd=usage,
            total_usd=limit,
            remaining_usd=max(limit - usage, 0.0),
            pct_used=_pct(usage, limit),
            source="key",
            usage_monthly_usd=monthly,
            limit_reset=reset_s,
            unlimited=False,
        )

    if budget_usd > 0:
        return UsageSnapshot(
            usage_usd=usage,
            total_usd=float(budget_usd),
            remaining_usd=max(float(budget_usd) - usage, 0.0),
            pct_used=_pct(usage, float(budget_usd)),
            source="key",
            usage_monthly_usd=monthly,
            limit_reset=reset_s,
            unlimited=False,
        )

    return UsageSnapshot(
        usage_usd=usage,
        total_usd=0.0,
        remaining_usd=None,
        pct_used=0.0,
        source="key",
        usage_monthly_usd=monthly,
        limit_reset=reset_s,
        unlimited=True,
    )


def _merge(
    credits: UsageSnapshot | None, key: UsageSnapshot | None
) -> UsageSnapshot | None:
    if credits is None:
        return key
    if key is None:
        return credits
    return UsageSnapshot(
        usage_usd=credits.usage_usd,
        total_usd=credits.total_usd,
        remaining_usd=credits.remaining_usd,
        pct_used=credits.pct_used,
        source="credits",
        usage_monthly_usd=key.usage_monthly_usd,
        limit_reset=key.limit_reset,
        unlimited=False,
    )


async def _fetch_credits(client: httpx.AsyncClient, api_key: str) -> UsageSnapshot | None:
    r = await client.get(
        OPENROUTER_CREDITS_URL,
        headers={"Authorization": f"Bearer {api_key}"},
    )
    if r.status_code in {401, 403}:
        return None
    r.raise_for_status()
    data = (r.json() or {}).get("data") or {}
    return snapshot_from_credits(data if isinstance(data, dict) else {})


async def _fetch_key(client: httpx.AsyncClient, api_key: str) -> UsageSnapshot | None:
    r = await client.get(
        OPENROUTER_KEY_URL,
        headers={"Authorization": f"Bearer {api_key}"},
    )
    if r.status_code in {401, 403}:
        return None
    r.raise_for_status()
    data = (r.json() or {}).get("data") or {}
    if not isinstance(data, dict):
        return None
    return snapshot_from_key(data, budget_usd=settings.openrouter_budget_usd)


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
            credits = await _fetch_credits(client, api_key)
            key = await _fetch_key(client, api_key)
            snap = _merge(credits, key)
    except Exception:
        logger.exception("OpenRouter usage fetch failed")
        return _cache[1] if _cache else None

    if snap is not None:
        _cache = (now, snap)
    return snap


def _fmt_usd(n: float | None) -> str:
    if n is None:
        return "—"
    if n < 0.01:
        return f"${n:.4f}"
    return f"${n:.2f}"


def main() -> None:
    snap = asyncio.run(fetch_usage(force=True))
    if snap is None:
        print("OpenRouter: sin datos (key o /credits)", file=sys.stderr)
        sys.exit(1)
    d = snap.as_dict()
    total = _fmt_usd(d["total_usd"]) if d["total_usd"] else "—"
    print(f"quedan {_fmt_usd(d['remaining_usd'])}  (fuente {d['source']})")
    print(f"usado  {_fmt_usd(d['usage_usd'])} / {total}")
    print(f"mes    {_fmt_usd(d['usage_monthly_usd'])}")
    if d.get("limit_reset"):
        print(f"reset  {d['limit_reset']}")


if __name__ == "__main__":
    main()
