"""Europe/Madrid helpers for session days and prompt time context."""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

MADRID = ZoneInfo("Europe/Madrid")


def now_madrid() -> datetime:
    return datetime.now(MADRID)


def today_madrid() -> date:
    return now_madrid().date()


def session_date_str() -> str:
    return today_madrid().isoformat()


def format_now_for_prompt() -> str:
    return now_madrid().strftime("%Y-%m-%d %H:%M %Z")
