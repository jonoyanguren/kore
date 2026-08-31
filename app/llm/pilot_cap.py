"""Per-home monthly LLM cap (shared OpenRouter key)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from fastapi import HTTPException, status

from app.accounts.context import current_profile
from app.config import settings
from app.storage.memory import MemoryStore
from app.timeutil import MADRID, now_madrid

USER_MSG = (
    "Has llegado al tope de LLM de este mes. "
    "Chat, misiones y dream vuelven el día 1."
)
DETAIL = "llm_cap"


@dataclass(frozen=True)
class CapStatus:
    used_usd: float
    cap_usd: float
    remaining_usd: float
    pct_used: float
    unlimited: bool
    blocked: bool
    day_from: str
    day_to: str

    def as_usage_dict(self) -> dict[str, object]:
        remaining_pct = 100.0 if self.unlimited else round(max(0.0, 100.0 - self.pct_used), 1)
        return {
            "usage_usd": round(self.used_usd, 4),
            "total_usd": round(self.cap_usd, 4),
            "remaining_usd": round(self.remaining_usd, 4),
            "pct_used": round(self.pct_used, 1),
            "remaining_pct": remaining_pct,
            "source": "home",
            "unlimited": self.unlimited,
            "blocked": self.blocked,
            "day_from": self.day_from,
            "day_to": self.day_to,
        }


def month_day_from_to() -> tuple[str, str]:
    today = now_madrid().date()
    return today.replace(day=1).isoformat(), today.isoformat()


def next_month_iso() -> str:
    today = now_madrid().date()
    if today.month == 12:
        nxt = date(today.year + 1, 1, 1)
    else:
        nxt = date(today.year, today.month + 1, 1)
    return datetime(nxt.year, nxt.month, nxt.day, 0, 5, tzinfo=MADRID).replace(
        microsecond=0
    ).isoformat()


def cap_usd() -> float:
    profile = current_profile.get()
    if profile is not None and profile.llm_cap_usd is not None:
        return max(0.0, float(profile.llm_cap_usd))
    return max(0.0, float(settings.pilot_llm_cap_usd or 0.0))


async def status_for(store: MemoryStore) -> CapStatus:
    day_from, day_to = month_day_from_to()
    summary = await store.summarize_llm_spend(day_from=day_from, day_to=day_to)
    used = float(summary.get("usd") or 0.0)
    cap = cap_usd()
    unlimited = cap <= 0
    remaining = 0.0 if unlimited else max(0.0, cap - used)
    pct = 0.0 if unlimited or cap <= 0 else min(100.0, (used / cap) * 100.0)
    blocked = (not unlimited) and used >= cap
    return CapStatus(
        used_usd=used,
        cap_usd=cap,
        remaining_usd=remaining,
        pct_used=pct,
        unlimited=unlimited,
        blocked=blocked,
        day_from=day_from,
        day_to=day_to,
    )


async def is_blocked(store: MemoryStore) -> bool:
    return (await status_for(store)).blocked


def http_cap() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        detail=DETAIL,
    )


async def require_under_cap(store: MemoryStore) -> None:
    if await is_blocked(store):
        raise http_cap()
