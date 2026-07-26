"""Europe/Madrid helpers for session days and prompt time context."""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

MADRID = ZoneInfo("Europe/Madrid")

_WEEKDAYS_ES = (
    "lunes",
    "martes",
    "miércoles",
    "jueves",
    "viernes",
    "sábado",
    "domingo",
)
_MONTHS_ES = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)


def now_madrid() -> datetime:
    return datetime.now(MADRID)


def today_madrid() -> date:
    return now_madrid().date()


def session_date_str() -> str:
    return today_madrid().isoformat()


def format_now_for_prompt() -> str:
    return now_madrid().strftime("%Y-%m-%d %H:%M %Z")


def format_madrid_clock() -> str:
    """Human-readable Madrid clock for /hora and the get_madrid_time tool."""
    now = now_madrid()
    weekday = _WEEKDAYS_ES[now.weekday()]
    month = _MONTHS_ES[now.month - 1]
    return (
        f"{weekday} {now.day} de {month} de {now.year}, "
        f"{now.strftime('%H:%M:%S')} (Europe/Madrid, {now.tzname()})"
    )


def madrid_time_payload() -> dict[str, str]:
    """Structured snapshot for tools / debugging."""
    now = now_madrid()
    return {
        "timezone": "Europe/Madrid",
        "iso": now.isoformat(timespec="seconds"),
        "date": now.date().isoformat(),
        "time": now.strftime("%H:%M:%S"),
        "weekday": _WEEKDAYS_ES[now.weekday()],
        "human": format_madrid_clock(),
    }
