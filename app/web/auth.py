"""Console auth: session cookie, email/password, or legacy CONSOLE_SECRET."""

from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import Cookie, Depends, Header, HTTPException, Request, status

from app.accounts.context import bind_tenant
from app.accounts.homes import Homes
from app.accounts.store import AccountStore, UserRow
from app.config import settings

COOKIE_NAME = "kore_console"
SESSION_MAX_AGE = 60 * 60 * 24 * 30


def console_secret_configured() -> str:
    return (settings.console_secret or "").strip()


def _secrets_match(provided: str, expected: str) -> bool:
    if not expected or not provided:
        return False
    if len(provided) != len(expected):
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


def accounts_of(request: Request) -> AccountStore | None:
    return getattr(request.app.state, "accounts", None)


def homes_of(request: Request) -> Homes | None:
    return getattr(request.app.state, "homes", None)


async def resolve_user(
    request: Request, token: str | None
) -> UserRow | None:
    if not token:
        return None
    accounts = accounts_of(request)
    if accounts is None:
        return None
    user = await accounts.user_for_session(token)
    if user is not None:
        if not user.allowed:
            return None
        return user
    if _secrets_match(token, console_secret_configured()):
        legacy = await accounts.legacy_user()
        if legacy is not None and not legacy.allowed:
            return None
        return legacy
    return None


async def bind_home(request: Request, user: UserRow) -> None:
    homes = homes_of(request)
    if homes is None:
        return
    home = await homes.open(user.id)
    request.state.user = user
    request.state.memory = home.memory
    request.state.vault = home.vault
    request.state.home = home
    bind_tenant(
        memory=home.memory,
        vault=home.vault,
        profile=user.profile(),
        gmail_tokens=home.gmail_tokens,
    )


async def require_console_auth(
    request: Request,
    provided: Annotated[str | None, Depends(extract_console_secret)],
) -> None:
    user = await resolve_user(request, provided)
    if user is not None:
        await bind_home(request, user)
        from app.billing.access import (
            billing_enforced,
            billing_ok,
            path_skips_billing,
        )

        if (
            billing_enforced()
            and not billing_ok(user)
            and not path_skips_billing(request.url.path)
        ):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="billing_required",
            )
        return
    expected = console_secret_configured()
    if _secrets_match(provided or "", expected):
        return
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="unauthorized",
    )
