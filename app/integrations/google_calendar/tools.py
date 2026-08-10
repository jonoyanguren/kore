"""LLM tools for Google Calendar (read-only)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from app.integrations.gmail.client import (
    GmailApiError,
    GmailConfigError,
    GmailNotConnectedError,
)
from app.integrations.google_calendar.client import CalendarClient
from app.llm.llm_assistant import ToolHandler
from app.timeutil import today_madrid

MADRID = ZoneInfo("Europe/Madrid")


def build_calendar_tools(
    calendar: CalendarClient | None,
) -> tuple[list[dict[str, Any]], dict[str, ToolHandler]]:
    if calendar is None:
        return [], {}

    schemas: list[dict[str, Any]] = [
        {
            "type": "function",
            "function": {
                "name": "list_calendar",
                "description": (
                    "Lista eventos de tu Google Calendar principal (no suscripciones "
                    "ni calendarios ajenos). Ventana por defecto: hoy → +3 días (Madrid). "
                    "Usa esto para saber citas reales; la agenda local es solo captura chat."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "from_day": {
                            "type": "string",
                            "description": "YYYY-MM-DD inicio (default hoy Madrid).",
                        },
                        "days": {
                            "type": "integer",
                            "description": "Días a mirar desde from_day (1–14). Default 4.",
                        },
                    },
                },
            },
        },
    ]

    async def list_calendar(args: dict[str, Any]) -> str:
        from_day = str(args.get("from_day") or "").strip() or today_madrid().isoformat()
        days = int(args.get("days") or 4)
        days = max(1, min(days, 14))
        try:
            start_d = datetime.fromisoformat(from_day).date()
        except ValueError:
            return json.dumps({"ok": False, "error": "invalid_from_day"})
        time_min = datetime.combine(start_d, datetime.min.time(), tzinfo=MADRID)
        time_max = time_min + timedelta(days=days)
        try:
            events = await calendar.list_events(
                time_min=time_min,
                time_max=time_max,
                max_total=50,
            )
        except GmailNotConnectedError:
            return json.dumps(
                {
                    "ok": False,
                    "error": "google_not_connected",
                    "hint": "Conecta Google en Más → Gmail (incluye Calendar).",
                }
            )
        except GmailConfigError as exc:
            return json.dumps(
                {"ok": False, "error": "google_not_configured", "detail": str(exc)}
            )
        except GmailApiError as exc:
            return json.dumps({"ok": False, "error": exc.code, "detail": exc.message})
        except Exception as exc:
            return json.dumps(
                {"ok": False, "error": "calendar_api_error", "detail": str(exc)}
            )
        return json.dumps(
            {
                "ok": True,
                "from_day": from_day,
                "days": days,
                "count": len(events),
                "events": [
                    {
                        "id": e.id,
                        "title": e.title,
                        "starts_at": e.starts_at,
                        "ends_at": e.ends_at,
                        "all_day": e.all_day,
                        "calendar": e.calendar_name,
                        "html_link": e.html_link,
                    }
                    for e in events
                ],
            },
            ensure_ascii=False,
        )

    return schemas, {"list_calendar": list_calendar}
