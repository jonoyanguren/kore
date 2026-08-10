"""Per-request stash for calendar block proposals (chat → confirm UI)."""

from __future__ import annotations

import contextvars
from typing import Any

_proposal: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar(
    "calendar_block_proposal", default=None
)


def set_calendar_proposal(proposal: dict[str, Any] | None) -> None:
    _proposal.set(proposal)


def take_calendar_proposal() -> dict[str, Any] | None:
    value = _proposal.get()
    _proposal.set(None)
    return value
