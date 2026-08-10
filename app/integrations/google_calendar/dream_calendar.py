"""Format Google Calendar events for morning dream payload."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.integrations.google_calendar.client import CalendarClient
from app.timeutil import today_madrid

logger = logging.getLogger(__name__)

MADRID = ZoneInfo("Europe/Madrid")
DREAM_CAL_DAYS = 4
DREAM_CAL_MAX = 25


async def fetch_calendar_block_for_dream(calendar: CalendarClient | None) -> str:
    if calendar is None:
        return "(Google Calendar no disponible en este proceso)"
    st = calendar.status()
    if not st.get("connected"):
        return "(Google no conectado — Más → Gmail)"
    if not st.get("calendar_ready"):
        return "(Sin permiso calendar.readonly — reconectar en Más → Gmail)"
    start = datetime.combine(today_madrid(), datetime.min.time(), tzinfo=MADRID)
    end = start + timedelta(days=DREAM_CAL_DAYS)
    try:
        events = await calendar.list_events(
            time_min=start,
            time_max=end,
            max_total=DREAM_CAL_MAX,
        )
    except Exception:
        logger.exception("Dream: failed listing Google Calendar")
        return "(No se pudo leer Google Calendar ahora)"
    if not events:
        return "(Sin eventos en los próximos días)"
    lines: list[str] = []
    for i, e in enumerate(events, start=1):
        cal = f" [{e.calendar_name}]" if e.calendar_name else ""
        lines.append(f"{i}. {e.starts_at} — {e.title}{cal}")
    return "\n".join(lines)
