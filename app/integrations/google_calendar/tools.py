"""LLM tools for Google Calendar (list + create + delete)."""

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
from app.integrations.google_calendar.propose_stash import (
    set_calendar_created,
    set_calendar_deleted,
)
from app.llm.llm_assistant import ToolHandler
from app.timeutil import (
    _WEEKDAYS_ES,
    resolve_relative_date,
    today_madrid,
)

MADRID = ZoneInfo("Europe/Madrid")


def _apply_day_phrase(starts_at: str, ends_at: str, day_phrase: str) -> tuple[str, str, str]:
    """Override dates with resolve_relative_date(day_phrase); keep wall times."""
    resolved = resolve_relative_date(day_phrase)
    if resolved is None:
        raise GmailApiError(
            "invalid",
            f"No entendí el día «{day_phrase}». Usa resolve_madrid_date o pregunta.",
        )
    start_dt = _parse_local_wall(starts_at)
    end_dt = _parse_local_wall(ends_at)
    start_dt = start_dt.replace(
        year=resolved.year, month=resolved.month, day=resolved.day
    )
    end_dt = end_dt.replace(
        year=resolved.year, month=resolved.month, day=resolved.day
    )
    if end_dt <= start_dt:
        # overnight block: push end to next day
        end_dt = end_dt + timedelta(days=1)
    return (
        start_dt.strftime("%Y-%m-%dT%H:%M"),
        end_dt.strftime("%Y-%m-%dT%H:%M"),
        _WEEKDAYS_ES[resolved.weekday()],
    )


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
                    "Úsala para ver qué hay, o para localizar el id/hora de un evento "
                    "antes de borrarlo. No la uses como validación inútil antes de crear "
                    "si Jon ya dio título y horario claros."
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
                    "Si Jon dice un día relativo (miércoles, mañana, el lunes…), "
                    "pasa day_phrase con esa frase: la fecha se calcula en servidor "
                    "(no inventes el día del mes). "
                    "Si solo da ISO claro, day_phrase puede ir vacío. "
                    "Una sola llamada; no pidas confirmación."
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
                            "description": (
                                "Inicio Madrid YYYY-MM-DDTHH:MM. Si hay day_phrase, "
                                "la fecha se sustituye; la hora sí cuenta."
                            ),
                        },
                        "ends_at": {
                            "type": "string",
                            "description": "Fin Madrid YYYY-MM-DDTHH:MM (misma regla).",
                        },
                        "day_phrase": {
                            "type": "string",
                            "description": (
                                "Frase del día: 'miércoles', 'mañana', "
                                "'el jueves que viene'. Obligatoria si mencionó un "
                                "día de la semana o relativo."
                            ),
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
        {
            "type": "function",
            "function": {
                "name": "delete_calendar_block",
                "description": (
                    "Borra un evento del Google Calendar primary. "
                    "Cuando Jon pide quitar/borrar/cancelar un bloque concreto, "
                    "hazlo (ya lo pidió). Pasa event_id si lo tienes de list_calendar; "
                    "si no, starts_at (+ title opcional) para localizarlo."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "event_id": {
                            "type": "string",
                            "description": "Id Google del evento (o gcal:…).",
                        },
                        "starts_at": {
                            "type": "string",
                            "description": "Inicio aprox. YYYY-MM-DDTHH:MM para buscar.",
                        },
                        "title": {
                            "type": "string",
                            "description": "Título o fragmento para desambiguar.",
                        },
                        "day_phrase": {
                            "type": "string",
                            "description": (
                                "Si Jon dice 'el de mañana 10:30', pasa day_phrase "
                                "y la hora en starts_at."
                            ),
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
                        "weekday": (
                            _WEEKDAYS_ES[_parse_local_wall(e.starts_at).weekday()]
                            if e.starts_at and "T" in e.starts_at
                            else ""
                        ),
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
        day_phrase = str(args.get("day_phrase") or "").strip()
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
        weekday_es = ""
        if day_phrase:
            try:
                starts_at, ends_at, weekday_es = _apply_day_phrase(
                    starts_at, ends_at, day_phrase
                )
            except GmailApiError as exc:
                return json.dumps({"ok": False, "error": exc.code, "detail": exc.message})
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

        if not weekday_es and ev.starts_at and "T" in ev.starts_at:
            try:
                weekday_es = _WEEKDAYS_ES[_parse_local_wall(ev.starts_at).weekday()]
            except GmailApiError:
                weekday_es = ""

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
                    "weekday": weekday_es,
                    "html_link": ev.html_link,
                },
                "say": (
                    f"{weekday_es} {ev.starts_at[8:10]} {ev.starts_at[11:16]}"
                    if weekday_es and len(ev.starts_at) >= 16
                    else ev.starts_at
                ),
            },
            ensure_ascii=False,
        )

    async def delete_calendar_block(args: dict[str, Any]) -> str:
        event_id = str(args.get("event_id") or "").strip()
        starts_at = str(args.get("starts_at") or "").strip()
        title = str(args.get("title") or "").strip().lower()
        day_phrase = str(args.get("day_phrase") or "").strip()

        if day_phrase and starts_at:
            try:
                starts_at, _, _ = _apply_day_phrase(
                    starts_at,
                    starts_at if "T" in starts_at else f"{starts_at[:10]}T00:00",
                    day_phrase,
                )
            except GmailApiError as exc:
                return json.dumps({"ok": False, "error": exc.code, "detail": exc.message})
        elif day_phrase and not starts_at:
            resolved = resolve_relative_date(day_phrase)
            if resolved is None:
                return json.dumps(
                    {"ok": False, "error": "invalid", "detail": "No entendí el día"}
                )
            starts_at = f"{resolved.isoformat()}T12:00"

        try:
            if not event_id:
                if not starts_at:
                    return json.dumps(
                        {
                            "ok": False,
                            "error": "missing_fields",
                            "hint": "Pasa event_id o starts_at (+ title).",
                        }
                    )
                anchor = _parse_local_wall(starts_at)
                window = await calendar.list_events(
                    time_min=anchor - timedelta(hours=1),
                    time_max=anchor + timedelta(hours=2),
                    max_total=30,
                )
                matches = []
                for ev in window:
                    if ev.all_day:
                        continue
                    try:
                        ev_start = _parse_local_wall(ev.starts_at)
                    except GmailApiError:
                        continue
                    same_slot = abs((ev_start - anchor).total_seconds()) <= 45 * 60
                    title_ok = (not title) or title in (ev.title or "").lower()
                    if same_slot and title_ok:
                        matches.append(ev)
                if not matches and title:
                    matches = [
                        ev
                        for ev in window
                        if title in (ev.title or "").lower() and not ev.all_day
                    ]
                if len(matches) == 0:
                    return json.dumps(
                        {
                            "ok": False,
                            "error": "not_found",
                            "detail": "No encontré ese bloque. Prueba list_calendar.",
                        }
                    )
                if len(matches) > 1 and not title:
                    return json.dumps(
                        {
                            "ok": False,
                            "error": "ambiguous",
                            "candidates": [
                                {
                                    "id": m.id,
                                    "title": m.title,
                                    "starts_at": m.starts_at,
                                }
                                for m in matches[:5]
                            ],
                            "hint": "Pasa title o event_id.",
                        },
                        ensure_ascii=False,
                    )
                target = matches[0]
                event_id = target.id
                deleted_meta = {
                    "title": target.title,
                    "starts_at": target.starts_at,
                    "ends_at": target.ends_at,
                }
            else:
                deleted_meta = {"event_id": event_id}

            await calendar.delete_event(event_id=event_id)
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

        set_calendar_deleted(deleted_meta)
        return json.dumps(
            {"ok": True, "deleted": True, "event": deleted_meta},
            ensure_ascii=False,
        )

    return schemas, {
        "list_calendar": list_calendar,
        "create_calendar_block": create_calendar_block,
        "delete_calendar_block": delete_calendar_block,
    }
