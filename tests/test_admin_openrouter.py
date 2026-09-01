"""Admin (legacy) sees shared OpenRouter remaining; other users do not."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.accounts.homes import Homes
from app.accounts.store import AccountStore
from app.config import settings
from app.llm.openrouter_credits import UsageSnapshot
from app.web.api import router as console_api_router


async def _run() -> None:
    old = (
        settings.console_secret,
        settings.storage_db_path,
        settings.vault_root,
    )
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        settings.console_secret = "test-console-secret-32chars-xxxx"
        settings.storage_db_path = str(root / "kore.db")
        settings.vault_root = str(root / "vault")
        try:
            accounts = AccountStore(str(root / "accounts.db"))
            await accounts.init()
            homes = Homes(accounts)
            app = FastAPI()
            app.include_router(console_api_router)
            app.state.accounts = accounts
            app.state.homes = homes
            transport = ASGITransport(app=app)
            snap = UsageSnapshot(
                usage_usd=12.0,
                total_usd=50.0,
                pct_used=24.0,
                source="credits",
                remaining_usd=38.0,
                usage_monthly_usd=2.5,
            )
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                await accounts.create_user(
                    email="jon@kore.local",
                    password="password1",
                    owner_name="Jon",
                    legacy_prompts=True,
                    onboarded=True,
                )
                login = await ac.post(
                    "/api/login",
                    json={"email": "jon@kore.local", "password": "password1"},
                )
                assert login.status_code == 200, login.text
                assert login.json()["user"]["admin"] is True

                with patch(
                    "app.web.api.fetch_usage",
                    new_callable=AsyncMock,
                    return_value=snap,
                ):
                    usage = await ac.get("/api/usage")
                assert usage.status_code == 200
                provider = usage.json()["provider"]
                assert provider is not None
                assert provider["remaining_usd"] == 38.0
                assert provider["source"] == "credits"

                await ac.post("/api/logout")
                other = await ac.post(
                    "/api/register",
                    json={"email": "ana@example.com", "password": "password1"},
                )
                assert other.status_code == 200
                assert other.json()["user"]["admin"] is False
                with patch(
                    "app.web.api.fetch_usage",
                    new_callable=AsyncMock,
                    return_value=snap,
                ) as fetch:
                    usage2 = await ac.get("/api/usage")
                assert usage2.status_code == 200
                assert usage2.json()["provider"] is None
                fetch.assert_not_called()
        finally:
            (
                settings.console_secret,
                settings.storage_db_path,
                settings.vault_root,
            ) = old


def test_admin_sees_openrouter_provider():
    asyncio.run(_run())
