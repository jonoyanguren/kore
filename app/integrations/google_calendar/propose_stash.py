"""Per-request stash for calendar mutations from chat tools."""

from __future__ import annotations

import contextvars
from typing import Any

_created: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar(
    "calendar_block_created", default=None
)
_deleted: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar(
    "calendar_block_deleted", default=None
)


def set_calendar_created(event: dict[str, Any] | None) -> None:
    _created.set(event)


def take_calendar_created() -> dict[str, Any] | None:
    value = _created.get()
    _created.set(None)
    return value


def set_calendar_deleted(info: dict[str, Any] | None) -> None:
    _deleted.set(info)


def take_calendar_deleted() -> dict[str, Any] | None:
    value = _deleted.get()
    _deleted.set(None)
    return value


def clear_calendar_stash() -> None:
    _created.set(None)
    _deleted.set(None)
