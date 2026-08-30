"""Pilot allowlist: only invited emails can register."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.accounts.allowlist import email_on_allowlist, parse_allowlist
from app.accounts.homes import Homes
from app.accounts.store import AccountStore
from app.config import settings
from app.web.api import router as console_api_router


def test_parse_allowlist():
    assert parse_allowlist("") == frozenset()
    assert parse_allowlist("Ana@X.com, bob@y.com") == frozenset(
        {"ana@x.com", "bob@y.com"}
    )
    assert email_on_allowlist("ana@x.com", "Ana@X.com") is True
    assert email_on_allowlist("eve@x.com", "Ana@X.com") is False
    assert email_on_allowlist("ana@x.com", "") is False


async def _register_gate() -> None:
    old = settings.pilot_allowlist
    try:
        settings.pilot_allowlist = ""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            accounts = AccountStore(str(root / "accounts.db"))
            await accounts.init()
            homes = Homes(accounts)
            app = FastAPI()
            app.include_router(console_api_router)
            app.state.accounts = accounts
            app.state.homes = homes
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                pub = await ac.get("/api/public/pilot")
                assert pub.status_code == 200
                assert pub.json()["invite_only"] is True

                blocked = await ac.post(
                    "/api/register",
                    json={"email": "eve@example.com", "password": "password1"},
                )
                assert blocked.status_code == 403
                assert blocked.json()["detail"] == "invite_required"

                settings.pilot_allowlist = "eve@example.com"
                ok = await ac.post(
                    "/api/register",
                    json={"email": "eve@example.com", "password": "password1"},
                )
                assert ok.status_code == 200, ok.text
    finally:
        settings.pilot_allowlist = old


def test_register_requires_allowlist():
    asyncio.run(_register_gate())
