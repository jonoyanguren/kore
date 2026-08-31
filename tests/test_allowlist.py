"""Registration is open; payment is the gate."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.accounts.homes import Homes
from app.accounts.store import AccountStore
from app.config import settings
from app.web.api import router as console_api_router


async def _register_open() -> None:
    old = (settings.console_secret, settings.storage_db_path, settings.vault_root)
    try:
        settings.console_secret = "test-console-secret-32chars-xxxx"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            settings.storage_db_path = str(root / "kore.db")
            settings.vault_root = str(root / "vault")
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
                assert "invite_only" not in pub.json()
                assert [p["id"] for p in pub.json()["plans"]] == ["5", "10", "20"]

                created = await ac.post(
                    "/api/register",
                    json={"email": "eve@example.com", "password": "password1"},
                )
                assert created.status_code == 200, created.text
                assert created.json()["user"]["email"] == "eve@example.com"
    finally:
        settings.console_secret, settings.storage_db_path, settings.vault_root = old


def test_register_is_open():
    asyncio.run(_register_open())
