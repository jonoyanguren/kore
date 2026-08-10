"""Per-request stash for calendar blocks created in chat."""

from __future__ import annotations

import contextvars
from typing import Any

_created: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar(
    "calendar_block_created", default=None
)


def set_calendar_created(event: dict[str, Any] | None) -> None:
    _created.set(event)


def take_calendar_created() -> dict[str, Any] | None:
    value = _created.get()
    _created.set(None)
    return value
