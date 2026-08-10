"""LLM tools for Google Calendar (read + propose write)."""

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
from app.integrations.google_calendar.client import CalendarClient, _parse_local_wall
from app.integrations.google_calendar.propose_stash import set_calendar_proposal
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
        {
            "type": "function",
            "function": {
                "name": "propose_calendar_block",
                "description": (
                    "Propone crear un bloque/evento en Google Calendar (primary). "
                    "NO crea el evento: la consola muestra un borrador editable para que "
                    "Jon confirme. Usa esto cuando pida reservar tiempo, foco, bloque, "
                    "cita, o meter algo en el calendario. Horas en Europe/Madrid "
                    "(YYYY-MM-DDTHH:MM). Antes conviene list_calendar si hay duda de huecos."
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
                        "reason": {
                            "type": "string",
                            "description": "Por qué este hueco (1 frase, para la card).",
                        },
                        "description": {
                            "type": "string",
                            "description": "Notas opcionales del evento en Calendar.",
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

    async def propose_calendar_block(args: dict[str, Any]) -> str:
        title = str(args.get("title") or "").strip()
        starts_at = str(args.get("starts_at") or "").strip()
        ends_at = str(args.get("ends_at") or "").strip()
        reason = str(args.get("reason") or "").strip()
        description = str(args.get("description") or "").strip()
        if not title or not starts_at or not ends_at:
            return json.dumps(
                {"ok": False, "error": "missing_fields", "need": ["title", "starts_at", "ends_at"]}
            )
        try:
            start_dt = _parse_local_wall(starts_at)
            end_dt = _parse_local_wall(ends_at)
        except GmailApiError as exc:
            return json.dumps({"ok": False, "error": exc.code, "detail": exc.message})
        if end_dt <= start_dt:
            return json.dumps(
                {"ok": False, "error": "invalid_range", "detail": "ends_at must be after starts_at"}
            )

        starts_norm = start_dt.strftime("%Y-%m-%dT%H:%M")
        ends_norm = end_dt.strftime("%Y-%m-%dT%H:%M")
        conflicts: list[dict[str, str]] = []
        try:
            overlapping = await calendar.list_events(
                time_min=start_dt - timedelta(minutes=1),
                time_max=end_dt + timedelta(minutes=1),
                max_total=20,
            )
            for ev in overlapping:
                if ev.all_day:
                    continue
                try:
                    ev_start = _parse_local_wall(ev.starts_at)
                    ev_end = _parse_local_wall(ev.ends_at or ev.starts_at)
                except GmailApiError:
                    continue
                if ev_start < end_dt and ev_end > start_dt:
                    conflicts.append(
                        {
                            "title": ev.title,
                            "starts_at": ev.starts_at,
                            "ends_at": ev.ends_at,
                        }
                    )
        except Exception:
            # Conflicts are advisory; proposal still OK
            pass

        can_write = calendar.can_write()
        proposal = {
            "title": title[:200],
            "starts_at": starts_norm,
            "ends_at": ends_norm,
            "reason": reason[:300],
            "description": description[:2000],
            "conflicts": conflicts[:8],
            "can_write": can_write,
        }
        set_calendar_proposal(proposal)
        return json.dumps(
            {
                "ok": True,
                "proposed": True,
                "awaiting_confirm": True,
                "can_write": can_write,
                "conflicts": conflicts[:8],
                "hint": (
                    "Borrador listo en la consola. Jon debe pulsar Crear. "
                    if can_write
                    else "Jon debe Reconectar en Más → Gmail (permiso calendar.events) "
                    "antes de poder crear."
                ),
                "title": proposal["title"],
                "starts_at": starts_norm,
                "ends_at": ends_norm,
            },
            ensure_ascii=False,
        )

    return schemas, {
        "list_calendar": list_calendar,
        "propose_calendar_block": propose_calendar_block,
    }
