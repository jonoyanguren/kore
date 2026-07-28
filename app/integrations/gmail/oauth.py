"""Google OAuth 2.0 (authorization code) for Gmail modify scope."""

from __future__ import annotations

import json
import logging
import secrets
import time
from pathlib import Path
from urllib.parse import urlencode

import httpx

from app.integrations.gmail.tokens import GMAIL_MODIFY_SCOPE, GmailTokens

logger = logging.getLogger(__name__)

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

# gmail.modify covers read + mark read / labels; not send.
SCOPES = (GMAIL_MODIFY_SCOPE, "openid", "email")


def oauth_state_path(storage_db_path: str) -> Path:
    return Path(storage_db_path).resolve().parent / "gmail_oauth_state.json"


def create_oauth_state(storage_db_path: str, ttl_seconds: float = 600.0) -> str:
    state = secrets.token_urlsafe(32)
    path = oauth_state_path(storage_db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"state": state, "expires_at": time.time() + ttl_seconds}) + "\n",
        encoding="utf-8",
    )
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return state


def consume_oauth_state(storage_db_path: str, provided: str) -> bool:
    path = oauth_state_path(storage_db_path)
    if not path.is_file():
        return False
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raw = None
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
    if not isinstance(raw, dict):
        return False
    expected = str(raw.get("state") or "")
    expires = float(raw.get("expires_at") or 0)
    if not expected or time.time() > expires:
        return False
    return secrets.compare_digest(expected, provided or "")


def build_authorize_url(
    *,
    client_id: str,
    redirect_uri: str,
    state: str,
) -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": state,
    }
    return f"{AUTH_URL}?{urlencode(params)}"


async def exchange_code(
    http: httpx.AsyncClient,
    *,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    code: str,
) -> GmailTokens:
    response = await http.post(
        TOKEN_URL,
        data={
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
        headers={"Accept": "application/json"},
    )
    response.raise_for_status()
    payload = response.json()
    expires_in = float(payload.get("expires_in") or 3600)
    tokens = GmailTokens(
        access_token=str(payload["access_token"]),
        refresh_token=str(payload.get("refresh_token") or ""),
        expires_at=time.time() + expires_in,
        token_type=str(payload.get("token_type") or "Bearer"),
        scope=str(payload.get("scope") or GMAIL_MODIFY_SCOPE),
    )
    if not tokens.refresh_token:
        logger.warning(
            "Google OAuth returned no refresh_token — re-consent may be needed"
        )
    email = await _fetch_email(http, tokens.access_token)
    if email:
        tokens.email = email
    return tokens


async def refresh_access_token(
    http: httpx.AsyncClient,
    *,
    client_id: str,
    client_secret: str,
    refresh_token: str,
) -> GmailTokens:
    response = await http.post(
        TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        headers={"Accept": "application/json"},
    )
    response.raise_for_status()
    payload = response.json()
    expires_in = float(payload.get("expires_in") or 3600)
    return GmailTokens(
        access_token=str(payload["access_token"]),
        refresh_token=refresh_token,
        expires_at=time.time() + expires_in,
        token_type=str(payload.get("token_type") or "Bearer"),
        scope=str(payload.get("scope") or GMAIL_MODIFY_SCOPE),
    )


async def _fetch_email(http: httpx.AsyncClient, access_token: str) -> str:
    try:
        response = await http.get(
            USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if response.status_code >= 400:
            return ""
        return str(response.json().get("email") or "")
    except Exception:
        logger.exception("Failed fetching Google userinfo email")
        return ""
