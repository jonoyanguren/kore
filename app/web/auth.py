"""Console auth: shared secret via cookie or Bearer."""

from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import Cookie, Depends, Header, HTTPException, status

from app.config import settings

COOKIE_NAME = "kore_console"


def console_secret_configured() -> str:
    return (settings.console_secret or "").strip()


def _secrets_match(provided: str, expected: str) -> bool:
    if not expected or not provided:
        return False
    if len(provided) != len(expected):
        # compare_digest requires equal length; avoid leaking via exception
        secrets.compare_digest(provided, provided)
        return False
    return secrets.compare_digest(provided, expected)


def extract_console_secret(
    authorization: Annotated[str | None, Header()] = None,
    kore_console: Annotated[str | None, Cookie(alias=COOKIE_NAME)] = None,
) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    if kore_console:
        return kore_console.strip()
    return None


def require_console_auth(
    provided: Annotated[str | None, Depends(extract_console_secret)],
) -> None:
    expected = console_secret_configured()
    if not _secrets_match(provided or "", expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="unauthorized",
        )
