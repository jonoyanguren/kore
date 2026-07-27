"""Europe/Madrid helpers for session days, clock, and natural Spanish dates."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
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

_WEEKDAY_ALIASES = {
    "lunes": 0,
    "martes": 1,
    "miercoles": 2,
    "miércoles": 2,
    "jueves": 3,
    "viernes": 4,
    "sabado": 5,
    "sábado": 5,
    "domingo": 6,
}


def now_madrid() -> datetime:
    return datetime.now(MADRID)


def today_madrid() -> date:
    return now_madrid().date()


def session_date_str() -> str:
    return today_madrid().isoformat()


def format_now_for_prompt() -> str:
    """Compact hint for system prompt (internal; chat uses spoken forms)."""
    now = now_madrid()
    return now.strftime("%Y-%m-%d %H:%M")


def format_madrid_clock() -> str:
    """Readable clock for /hora — Spanish day/month/year, no timezone label."""
    now = now_madrid()
    weekday = _WEEKDAYS_ES[now.weekday()]
    month = _MONTHS_ES[now.month - 1]
    return (
        f"{weekday} {now.day} de {month} de {now.year}, "
        f"{now.strftime('%H:%M')}"
    )


def format_relative_es(
    created_at: str, *, now: datetime | None = None
) -> str:
    """Human relative time in Spanish for chat bubbles.

    Buckets: hace un momento → hace X min → hace una hora / X horas →
    ayer → weekday or "D de mes" further back.
    """
    now = now or now_madrid()
    raw = (created_at or "").strip()
    if not raw:
        return ""
    # SQLite datetime('now') is UTC-naive; accept ISO with Z/offset too.
    try:
        if raw.endswith("Z"):
            then = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        else:
            then = datetime.fromisoformat(raw)
        if then.tzinfo is None:
            then = then.replace(tzinfo=ZoneInfo("UTC")).astimezone(MADRID)
        else:
            then = then.astimezone(MADRID)
    except ValueError:
        return raw[:16]

    delta = now - then
    secs = int(delta.total_seconds())
    if secs < 0:
        secs = 0
    if secs < 90:
        return "hace un momento"
    mins = secs // 60
    if mins < 50:
        if mins == 1:
            return "hace un minuto"
        return f"hace {mins} minutos"
    hours = secs // 3600
    if hours < 24 and then.date() == now.date():
        if hours <= 1:
            return "hace una hora"
        return f"hace {hours} horas"
    days = (now.date() - then.date()).days
    if days == 1:
        return "ayer"
    if days == 2:
        return "hace un día"
    if days < 7:
        return f"el {_WEEKDAYS_ES[then.weekday()]}"
    month = _MONTHS_ES[then.month - 1]
    if then.year == now.year:
        return f"{then.day} de {month}"
    return f"{then.day} de {month} de {then.year}"


def _week_monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def format_date_spoken(target: date, *, ref: date | None = None) -> str:
    """Natural Spanish for chat — not a full formal date dump."""
    ref = ref or today_madrid()
    delta = (target - ref).days
    wd = _WEEKDAYS_ES[target.weekday()]

    if delta == 0:
        return "hoy"
    if delta == 1:
        return "mañana"
    if delta == -1:
        return "ayer"
    if delta == 2:
        return "pasado mañana"
    if delta == -2:
        return "anteayer"

    ref_mon = _week_monday(ref)
    target_mon = _week_monday(target)

    if target_mon == ref_mon:
        if target < ref:
            # Same week, already happened — "el lunes" / "el lunes 20"
            return f"el {wd} {target.day}"
        return f"el {wd} de esta semana"
    if target_mon == ref_mon + timedelta(days=7):
        return f"el {wd} que viene"
    if target_mon == ref_mon - timedelta(days=7):
        return f"el {wd} pasado"

    if target.year == ref.year and target.month == ref.month:
        return f"el {wd} {target.day}"
    if target.year == ref.year:
        return f"el {wd} {target.day} de {_MONTHS_ES[target.month - 1]}"
    return (
        f"el {wd} {target.day} de {_MONTHS_ES[target.month - 1]} "
        f"de {target.year}"
    )


def format_date_formal(target: date) -> str:
    """Full Spanish date when formality is needed (rare in chat)."""
    wd = _WEEKDAYS_ES[target.weekday()]
    month = _MONTHS_ES[target.month - 1]
    return f"{wd} {target.day} de {month} de {target.year}"


def _next_weekday(ref: date, weekday: int, *, weeks_ahead: int = 0) -> date:
    """Next occurrence of weekday; weeks_ahead=0 means this week's that day
    if still upcoming or today, else next week — see resolve logic."""
    days_ahead = (weekday - ref.weekday()) % 7
    return ref + timedelta(days=days_ahead + 7 * weeks_ahead)


def resolve_relative_date(phrase: str, *, ref: date | None = None) -> date | None:
    """Resolve common Spanish relative phrases to a calendar date (Madrid)."""
    ref = ref or today_madrid()
    text = (
        phrase.strip()
        .lower()
        .replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace("ñ", "n")
    )
    text = re.sub(r"\s+", " ", text)

    if text in {"hoy", "esta noche", "esta tarde", "esta manana"}:
        return ref
    if text in {"manana"}:
        return ref + timedelta(days=1)
    if text in {"pasado manana"}:
        return ref + timedelta(days=2)
    if text in {"ayer"}:
        return ref + timedelta(days=-1)
    if text in {"anteayer"}:
        return ref + timedelta(days=-2)

    # ISO already
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return date.fromisoformat(text)

    # "el lunes que viene" / "proximo lunes" / "el lunes de esta semana" / "este lunes"
    for name, weekday in _WEEKDAY_ALIASES.items():
        if name not in text:
            continue
        this_week = _week_monday(ref) + timedelta(days=weekday)
        if (
            "que viene" in text
            or "proxima" in text
            or "proximo" in text
            or "siguiente" in text
        ):
            return this_week + timedelta(days=7)
        if "pasado" in text and "pasado manana" not in text:
            return this_week - timedelta(days=7)
        if "esta semana" in text or re.search(rf"\beste\s+{name}\b", text):
            return this_week
        # bare "el lunes" / "lunes": upcoming occurrence (today counts)
        if this_week >= ref:
            return this_week
        return this_week + timedelta(days=7)

    return None


def madrid_time_payload() -> dict[str, str]:
    """Structured snapshot for get_madrid_time."""
    now = now_madrid()
    today = now.date()
    return {
        "date": today.isoformat(),
        "time": now.strftime("%H:%M"),
        "weekday": _WEEKDAYS_ES[now.weekday()],
        "human": format_madrid_clock(),
        "spoken_today": format_date_spoken(today, ref=today),
    }


def resolve_date_payload(phrase: str) -> dict[str, str]:
    """Resolve a relative phrase → ISO date + how to say it in chat."""
    ref = today_madrid()
    resolved = resolve_relative_date(phrase, ref=ref)
    if resolved is None:
        return {
            "ok": "false",
            "error": "No pude interpretar esa fecha relativa",
            "phrase": phrase,
            "ref_date": ref.isoformat(),
        }
    return {
        "ok": "true",
        "phrase": phrase,
        "date": resolved.isoformat(),
        "weekday": _WEEKDAYS_ES[resolved.weekday()],
        "spoken": format_date_spoken(resolved, ref=ref),
        "formal": format_date_formal(resolved),
        "ref_date": ref.isoformat(),
    }
