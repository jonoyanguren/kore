"""LLM tools for Google Calendar (read + create)."""

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
from app.integrations.google_calendar.client import (
    CalendarClient,
    _parse_local_wall,
    meeting_dict_from_event,
)
from app.integrations.google_calendar.propose_stash import set_calendar_created
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
                    "Lista eventos del Google Calendar principal. "
                    "Solo si Jon pregunta qué tiene, huecos libres, o si el día/hora "
                    "es ambiguo y necesitas mirar. NO llames esto antes de crear un "
                    "bloque cuando él ya dio título y horario claros."
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
        {
            "type": "function",
            "function": {
                "name": "create_calendar_block",
                "description": (
                    "Crea YA un evento en Google Calendar (primary). "
                    "Úsala en cuanto tengas título + inicio + fin claros — sin listar "
                    "antes, sin pedir confirmación, sin pasar por borrador. "
                    "Si falta día/hora o hay mucha duda, pregunta en texto (1 pregunta) "
                    "y no llames la tool. Horas Europe/Madrid YYYY-MM-DDTHH:MM."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Título corto del evento.",
                        },
                        "starts_at": {
                            "type": "string",
                            "description": "Inicio Madrid: YYYY-MM-DDTHH:MM",
                        },
                        "ends_at": {
                            "type": "string",
                            "description": "Fin Madrid: YYYY-MM-DDTHH:MM",
                        },
                        "description": {
                            "type": "string",
                            "description": "Notas opcionales del evento.",
                        },
                    },
                    "required": ["title", "starts_at", "ends_at"],
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

    async def create_calendar_block(args: dict[str, Any]) -> str:
        title = str(args.get("title") or "").strip()
        starts_at = str(args.get("starts_at") or "").strip()
        ends_at = str(args.get("ends_at") or "").strip()
        description = str(args.get("description") or "").strip()
        if not title or not starts_at or not ends_at:
            return json.dumps(
                {
                    "ok": False,
                    "error": "missing_fields",
                    "need": ["title", "starts_at", "ends_at"],
                    "hint": "Pregunta a Jon lo que falte; no inventes hora.",
                }
            )
        try:
            ev = await calendar.create_event(
                title=title,
                starts_at=starts_at,
                ends_at=ends_at,
                description=description,
            )
        except GmailNotConnectedError:
            return json.dumps(
                {
                    "ok": False,
                    "error": "google_not_connected",
                    "hint": "Conecta Google en Más → Gmail.",
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

        row = meeting_dict_from_event(ev)
        set_calendar_created(row)
        return json.dumps(
            {
                "ok": True,
                "created": True,
                "event": {
                    "title": ev.title,
                    "starts_at": ev.starts_at,
                    "ends_at": ev.ends_at,
                    "html_link": ev.html_link,
                },
            },
            ensure_ascii=False,
        )

    return schemas, {
        "list_calendar": list_calendar,
        "create_calendar_block": create_calendar_block,
    }
