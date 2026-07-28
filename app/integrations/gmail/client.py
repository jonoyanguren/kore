"""Thin Gmail REST wrapper (users.messages)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from app.config import settings
from app.integrations.gmail.oauth import refresh_access_token
from app.integrations.gmail.tokens import GmailTokenStore, GmailTokens

logger = logging.getLogger(__name__)

GMAIL_API = "https://gmail.googleapis.com/gmail/v1"


@dataclass
class GmailMessage:
    id: str
    thread_id: str
    subject: str
    from_: str
    snippet: str
    date: str
    unread: bool
    permalink: str


class GmailNotConnectedError(RuntimeError):
    pass


class GmailConfigError(RuntimeError):
    pass


class GmailClient:
    def __init__(
        self,
        http: httpx.AsyncClient,
        token_store: GmailTokenStore,
    ) -> None:
        self._http = http
        self._tokens = token_store

    def configured(self) -> bool:
        return bool(settings.google_client_id.strip() and settings.google_client_secret.strip())

    def connected(self) -> bool:
        return self._tokens.connected()

    def status(self) -> dict[str, Any]:
        tokens = self._tokens.load()
        return {
            "configured": self.configured(),
            "connected": bool(tokens and tokens.refresh_token),
            "email": (tokens.email if tokens else "") or "",
            "scope": "gmail.modify",
        }

    async def _access_headers(self) -> dict[str, str]:
        if not self.configured():
            raise GmailConfigError("GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET not set")
        tokens = self._tokens.load()
        if not tokens or not tokens.refresh_token:
            raise GmailNotConnectedError("Gmail not connected — open /api/gmail/connect")
        if not tokens.access_valid():
            refreshed = await refresh_access_token(
                self._http,
                client_id=settings.google_client_id,
                client_secret=settings.google_client_secret,
                refresh_token=tokens.refresh_token,
            )
            refreshed.email = tokens.email
            self._tokens.save(refreshed)
            tokens = refreshed
        return {"Authorization": f"Bearer {tokens.access_token}"}

    async def list_messages(
        self,
        *,
        query: str = "is:unread newer_than:1d",
        max_results: int = 15,
    ) -> list[GmailMessage]:
        headers = await self._access_headers()
        list_resp = await self._http.get(
            f"{GMAIL_API}/users/me/messages",
            headers=headers,
            params={"q": query, "maxResults": max(1, min(max_results, 50))},
        )
        list_resp.raise_for_status()
        ids = [m["id"] for m in list_resp.json().get("messages") or []]
        out: list[GmailMessage] = []
        for mid in ids:
            msg = await self.get_message(mid)
            if msg:
                out.append(msg)
        return out

    async def get_message(self, message_id: str) -> GmailMessage | None:
        headers = await self._access_headers()
        response = await self._http.get(
            f"{GMAIL_API}/users/me/messages/{message_id}",
            headers=headers,
            params={"format": "metadata", "metadataHeaders": ["From", "Subject", "Date"]},
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return _parse_message(response.json())

    async def mark_read(self, message_id: str) -> bool:
        headers = await self._access_headers()
        response = await self._http.post(
            f"{GMAIL_API}/users/me/messages/{message_id}/modify",
            headers=headers,
            json={"removeLabelIds": ["UNREAD"]},
        )
        if response.status_code == 404:
            return False
        response.raise_for_status()
        return True

    async def save_tokens(self, tokens: GmailTokens) -> None:
        existing = self._tokens.load()
        if existing and existing.refresh_token and not tokens.refresh_token:
            tokens.refresh_token = existing.refresh_token
        if existing and existing.email and not tokens.email:
            tokens.email = existing.email
        self._tokens.save(tokens)

    def disconnect(self) -> None:
        self._tokens.clear()


def _header_map(payload: dict[str, Any]) -> dict[str, str]:
    headers = (payload.get("payload") or {}).get("headers") or []
    out: dict[str, str] = {}
    for h in headers:
        name = str(h.get("name") or "").lower()
        if name:
            out[name] = str(h.get("value") or "")
    return out


def _parse_message(payload: dict[str, Any]) -> GmailMessage:
    headers = _header_map(payload)
    mid = str(payload.get("id") or "")
    label_ids = payload.get("labelIds") or []
    date_raw = headers.get("date", "")
    date_iso = date_raw
    if date_raw:
        try:
            date_iso = parsedate_to_datetime(date_raw).isoformat()
        except (TypeError, ValueError, IndexError):
            pass
    return GmailMessage(
        id=mid,
        thread_id=str(payload.get("threadId") or ""),
        subject=headers.get("subject") or "(sin asunto)",
        from_=headers.get("from") or "",
        snippet=str(payload.get("snippet") or ""),
        date=date_iso,
        unread="UNREAD" in label_ids,
        permalink=f"https://mail.google.com/mail/u/0/#inbox/{mid}",
    )
