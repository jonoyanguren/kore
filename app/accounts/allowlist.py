"""Pilot invite list: who may create a new account."""

from __future__ import annotations

from app.accounts.store import normalize_email
from app.config import settings


def parse_allowlist(raw: str) -> frozenset[str]:
    parts = (raw or "").replace(";", ",").split(",")
    return frozenset(normalize_email(p) for p in parts if p.strip())


def email_on_allowlist(email: str, raw: str | None = None) -> bool:
    listed = parse_allowlist(
        settings.pilot_allowlist if raw is None else raw
    )
    if not listed:
        return False
    return normalize_email(email) in listed
