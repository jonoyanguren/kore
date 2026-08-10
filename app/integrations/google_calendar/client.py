"""Google Calendar read-only client (shares Gmail OAuth tokens)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from app.integrations.gmail.client import (
    GmailApiError,
    GmailClient,
    GmailConfigError,
    GmailNotConnectedError,
)
from app.timeutil import today_madrid

logger = logging.getLogger(__name__)

CALENDAR_API = "https://www.googleapis.com/calendar/v3"
MADRID = ZoneInfo("Europe/Madrid")


@dataclass
class CalendarEvent:
    id: str
    calendar_id: str
    calendar_name: str
    title: str
    starts_at: str  # Madrid-local YYYY-MM-DD or YYYY-MM-DDTHH:MM
    ends_at: str
    all_day: bool
    html_link: str
    status: str


class CalendarClient:
    def __init__(self, http: httpx.AsyncClient, gmail: GmailClient) -> None:
        self._http = http
        self._gmail = gmail

    def status(self) -> dict[str, Any]:
        return self._gmail.status()

    def ready(self) -> bool:
        return bool(self._gmail.status().get("calendar_ready"))

    def can_write(self) -> bool:
        return bool(self._gmail.status().get("calendar_can_write"))

    async def create_event(
        self,
        *,
        title: str,
        starts_at: str,
        ends_at: str,
        description: str = "",
        calendar_id: str = "primary",
    ) -> CalendarEvent:
        """Create a timed event on the primary calendar (Madrid timezone)."""
        if not self._gmail.configured():
            raise GmailConfigError("GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET not set")
        st = self._gmail.status()
        if not st.get("connected"):
            raise GmailNotConnectedError("Google not connected — open /api/gmail/connect")
        if not st.get("calendar_can_write"):
            raise GmailApiError(
                "needs_reconnect",
                "Falta permiso para crear eventos. Reconecta en Más → Gmail "
                "y acepta Calendar (editar eventos).",
            )
        summary = (title or "").strip()
        if not summary:
            raise GmailApiError("invalid", "Falta título del evento.")
        start_dt = _parse_local_wall(starts_at)
        end_dt = _parse_local_wall(ends_at)
        if end_dt <= start_dt:
            raise GmailApiError("invalid", "La hora de fin debe ser después del inicio.")

        from urllib.parse import quote

        headers = await self._gmail.access_headers()
        body: dict[str, Any] = {
            "summary": summary[:500],
            "start": {
                "dateTime": start_dt.strftime("%Y-%m-%dT%H:%M:%S"),
                "timeZone": "Europe/Madrid",
            },
            "end": {
                "dateTime": end_dt.strftime("%Y-%m-%dT%H:%M:%S"),
                "timeZone": "Europe/Madrid",
            },
        }
        desc = (description or "").strip()
        if desc:
            body["description"] = desc[:8000]

        cid = (calendar_id or "primary").strip() or "primary"
        url = f"{CALENDAR_API}/calendars/{quote(cid, safe='')}/events"
        response = await self._http.post(url, headers=headers, json=body)
        if response.status_code >= 400:
            raise _calendar_http_error(response)
        item = response.json()
        if not isinstance(item, dict):
            raise GmailApiError("api", "Calendar no devolvió el evento creado.")
        cal_name = "primary" if cid == "primary" else cid
        ev = _parse_event(item, calendar_id=cid, calendar_name=cal_name)
        if ev is None:
            raise GmailApiError("api", "No se pudo leer el evento creado.")
        return ev

    async def list_events(
        self,
        *,
        time_min: datetime | None = None,
        time_max: datetime | None = None,
        max_per_calendar: int = 40,
        max_total: int = 80,
    ) -> list[CalendarEvent]:
        """List events from the user's primary Google Calendar only."""
        if not self._gmail.configured():
            raise GmailConfigError("GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET not set")
        st = self._gmail.status()
        if not st.get("connected"):
            raise GmailNotConnectedError("Google not connected — open /api/gmail/connect")
        if not st.get("calendar_ready"):
            raise GmailApiError(
                "needs_reconnect",
                "Falta permiso de Calendar. Desconecta y vuelve a conectar en Más → Gmail.",
            )

        start = time_min or datetime.combine(
            today_madrid(), datetime.min.time(), tzinfo=MADRID
        )
        end = time_max or (start + timedelta(days=4))
        if start.tzinfo is None:
            start = start.replace(tzinfo=MADRID)
        if end.tzinfo is None:
            end = end.replace(tzinfo=MADRID)

        headers = await self._gmail.access_headers()
        calendars = await self._list_calendars(headers)
        out: list[CalendarEvent] = []
        for cal in calendars:
            try:
                events = await self._list_calendar_events(
                    headers,
                    calendar_id=cal["id"],
                    calendar_name=cal["name"],
                    time_min=start,
                    time_max=end,
                    max_results=max_per_calendar,
                )
            except GmailApiError:
                raise
            except Exception:
                logger.exception("Calendar list failed for %s", cal.get("id"))
                continue
            out.extend(events)
            if len(out) >= max_total:
                break

        out.sort(key=lambda e: (e.starts_at, e.title.lower()))
        return out[:max_total]

    async def _list_calendars(self, headers: dict[str, str]) -> list[dict[str, str]]:
        """Return only the user's primary calendar (not subscribed/shared lists)."""
        response = await self._http.get(
            f"{CALENDAR_API}/users/me/calendarList",
            headers=headers,
            params={"minAccessRole": "reader", "maxResults": 100},
        )
        if response.status_code >= 400:
            raise _calendar_http_error(response)
        items = response.json().get("items") or []
        for item in items:
            if not isinstance(item, dict):
                continue
            if item.get("primary") is True:
                cid = str(item.get("id") or "primary").strip() or "primary"
                name = str(item.get("summary") or "primary").strip()
                return [{"id": cid, "name": name}]
        # Fallback if primary flag missing
        return [{"id": "primary", "name": "primary"}]

    async def _list_calendar_events(
        self,
        headers: dict[str, str],
        *,
        calendar_id: str,
        calendar_name: str,
        time_min: datetime,
        time_max: datetime,
        max_results: int,
    ) -> list[CalendarEvent]:
        from urllib.parse import quote

        params = {
            "timeMin": time_min.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "timeMax": time_max.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "singleEvents": "true",
            "orderBy": "startTime",
            "maxResults": max(1, min(max_results, 100)),
        }
        url = f"{CALENDAR_API}/calendars/{quote(calendar_id, safe='')}/events"
        response = await self._http.get(url, headers=headers, params=params)
        if response.status_code >= 400:
            raise _calendar_http_error(response)
        items = response.json().get("items") or []
        out: list[CalendarEvent] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            status = str(item.get("status") or "confirmed")
            if status == "cancelled":
                continue
            ev = _parse_event(item, calendar_id=calendar_id, calendar_name=calendar_name)
            if ev:
                out.append(ev)
        return out


def _parse_local_wall(raw: str) -> datetime:
    """Parse YYYY-MM-DDTHH:MM[.SS] as Europe/Madrid wall time."""
    text = (raw or "").strip().replace(" ", "T")
    if not text:
        raise GmailApiError("invalid", "Falta fecha/hora.")
    for n, fmt in ((19, "%Y-%m-%dT%H:%M:%S"), (16, "%Y-%m-%dT%H:%M")):
        try:
            return datetime.strptime(text[:n], fmt).replace(tzinfo=MADRID)
        except ValueError:
            continue
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            return dt.replace(tzinfo=MADRID)
        return dt.astimezone(MADRID)
    except ValueError as exc:
        raise GmailApiError(
            "invalid", f"Usa YYYY-MM-DDTHH:MM (Madrid). Recibido: {raw}"
        ) from exc


def _parse_event(
    item: dict[str, Any],
    *,
    calendar_id: str,
    calendar_name: str,
) -> CalendarEvent | None:
    eid = str(item.get("id") or "").strip()
    if not eid:
        return None
    start = item.get("start") or {}
    end = item.get("end") or {}
    all_day = "date" in start and "dateTime" not in start
    starts_at = _to_local_stamp(start)
    ends_at = _to_local_stamp(end)
    if not starts_at:
        return None
    title = str(item.get("summary") or "(sin título)").strip()
    return CalendarEvent(
        id=eid,
        calendar_id=calendar_id,
        calendar_name=calendar_name,
        title=title,
        starts_at=starts_at,
        ends_at=ends_at,
        all_day=all_day,
        html_link=str(item.get("htmlLink") or ""),
        status=str(item.get("status") or "confirmed"),
    )


def _to_local_stamp(block: dict[str, Any]) -> str:
    if not isinstance(block, dict):
        return ""
    if block.get("date"):
        # All-day: YYYY-MM-DD
        return str(block["date"])[:10]
    raw = str(block.get("dateTime") or "").strip()
    if not raw:
        return ""
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        local = dt.astimezone(MADRID)
        return local.strftime("%Y-%m-%dT%H:%M")
    except ValueError:
        return raw[:16]


def _calendar_http_error(response: httpx.Response) -> GmailApiError:
    body = ""
    try:
        body = response.text[:800]
    except Exception:
        pass
    low = body.lower()
    logger.warning(
        "Calendar API HTTP %s: %s",
        response.status_code,
        body[:300] if body else "(empty)",
    )
    if response.status_code == 403 and (
        "accessnotconfigured" in low
        or "has not been used" in low
        or "is disabled" in low
        or "api not enabled" in low
        or "service_disabled" in low
    ):
        return GmailApiError(
            "api_disabled",
            "Falta activar Google Calendar API en el proyecto GCP "
            "(mismo que el OAuth). "
            "https://console.cloud.google.com/apis/library/calendar-json.googleapis.com",
        )
    if response.status_code == 403 and (
        "insufficient" in low or "access_token_scope_insufficient" in low
    ):
        return GmailApiError(
            "needs_reconnect",
            "Falta permiso de Calendar. Desconecta y vuelve a conectar en Más → Gmail.",
        )
    if response.status_code in {401, 403}:
        return GmailApiError(
            "auth",
            "Calendar devolvió 403. Suele ser API no activada en GCP "
            "(calendar-json.googleapis.com), no un fallo de reconectar. "
            "https://console.cloud.google.com/apis/library/calendar-json.googleapis.com",
        )
    return GmailApiError(
        "api",
        "Google Calendar no respondió bien ahora. Prueba en un momento.",
    )


def meeting_dict_from_event(ev: CalendarEvent) -> dict[str, Any]:
    return {
        "id": f"gcal:{ev.calendar_id}:{ev.id}",
        "starts_at": ev.starts_at,
        "title": ev.title,
        "status": "planned",
        "source": "google",
        "calendar": ev.calendar_name,
        "html_link": ev.html_link or None,
        "ends_at": ev.ends_at or None,
        "all_day": ev.all_day,
    }


def merge_meetings(
    local: list[dict[str, Any]],
    google: list[dict[str, Any]],
    *,
    limit: int = 12,
) -> list[dict[str, Any]]:
    """Merge local agenda + Google events; prefer Google on near-duplicate titles/times."""
    normalized_local: list[dict[str, Any]] = []
    for m in local:
        row = dict(m)
        row.setdefault("source", "local")
        normalized_local.append(row)

    def key(m: dict[str, Any]) -> tuple[str, str]:
        starts = str(m.get("starts_at") or "")[:16]
        title = " ".join(str(m.get("title") or "").lower().split())
        return starts[:10], title

    google_keys = {key(m) for m in google}
    filtered_local = [m for m in normalized_local if key(m) not in google_keys]
    merged = google + filtered_local
    merged.sort(key=lambda m: (str(m.get("starts_at") or ""), str(m.get("title") or "")))
    return merged[:limit]
