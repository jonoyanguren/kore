"""Google Calendar helpers + OAuth scope."""

from __future__ import annotations

from app.integrations.gmail.oauth import build_authorize_url
from app.integrations.gmail.tokens import (
    CALENDAR_READONLY_SCOPE,
    scope_has_calendar,
)
from app.integrations.google_calendar.client import (
    CalendarEvent,
    meeting_dict_from_event,
    merge_meetings,
)


def test_scope_has_calendar():
    assert scope_has_calendar(CALENDAR_READONLY_SCOPE)
    assert scope_has_calendar(
        "openid email https://www.googleapis.com/auth/calendar.readonly"
    )
    assert not scope_has_calendar("https://www.googleapis.com/auth/gmail.modify")


def test_scope_can_write_calendar():
    from app.integrations.gmail.tokens import (
        CALENDAR_EVENTS_SCOPE,
        scope_can_write_calendar,
    )

    assert scope_can_write_calendar(CALENDAR_EVENTS_SCOPE)
    assert not scope_can_write_calendar(CALENDAR_READONLY_SCOPE)
    assert scope_can_write_calendar(
        "openid https://www.googleapis.com/auth/calendar.events"
    )
    assert scope_can_write_calendar("https://www.googleapis.com/auth/calendar")
    assert not scope_can_write_calendar(
        "https://www.googleapis.com/auth/calendar.events.readonly"
    )


def test_authorize_url_includes_calendar_scope():
    url = build_authorize_url(
        client_id="cid",
        redirect_uri="https://kore.fly.dev/api/gmail/callback",
        state="abc",
    )
    assert "calendar.readonly" in url
    assert "calendar.events" in url
    assert "gmail.modify" in url
    assert "gmail.send" in url


def test_parse_local_wall():
    from zoneinfo import ZoneInfo

    from app.integrations.google_calendar.client import _parse_local_wall

    dt = _parse_local_wall("2026-08-11T10:00")
    assert dt.hour == 10
    assert dt.tzinfo == ZoneInfo("Europe/Madrid")
    later = _parse_local_wall("2026-08-11T11:30")
    assert later > dt


def test_merge_meetings_prefers_google_on_duplicate():
    local = [
        {
            "id": 1,
            "starts_at": "2026-08-10T10:00",
            "title": "Standup",
            "status": "planned",
            "source": "local",
        },
        {
            "id": 2,
            "starts_at": "2026-08-10T15:00",
            "title": "Solo local",
            "status": "planned",
            "source": "local",
        },
    ]
    google = [
        meeting_dict_from_event(
            CalendarEvent(
                id="abc",
                calendar_id="primary",
                calendar_name="Jon",
                title="Standup",
                starts_at="2026-08-10T10:00",
                ends_at="2026-08-10T10:30",
                all_day=False,
                html_link="https://calendar.google.com/x",
                status="confirmed",
            )
        )
    ]
    merged = merge_meetings(local, google, limit=10)
    assert len(merged) == 2
    assert merged[0]["source"] == "google"
    assert merged[0]["title"] == "Standup"
    assert merged[1]["title"] == "Solo local"
    assert merged[1]["source"] == "local"


def test_meeting_dict_from_event():
    row = meeting_dict_from_event(
        CalendarEvent(
            id="e1",
            calendar_id="c1",
            calendar_name="Work",
            title="Sync",
            starts_at="2026-08-11T09:00",
            ends_at="2026-08-11T09:30",
            all_day=False,
            html_link="https://calendar.google.com/e1",
            status="confirmed",
        )
    )
    assert row["id"].startswith("gcal:")
    assert row["source"] == "google"
    assert row["calendar"] == "Work"
