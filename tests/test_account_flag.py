"""Account access flag: login and sessions respect `allowed`."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

import aiosqlite

from app.accounts.homes import Homes
from app.accounts.store import AccountStore
from app.config import settings
from app.web.api import router as console_api_router
from app.web.auth import COOKIE_NAME


async def _migrate_old_users_table() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = str(Path(tmp) / "accounts.db")
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                """
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    owner_name TEXT NOT NULL DEFAULT '',
                    companion_name TEXT NOT NULL DEFAULT '',
                    companion_tone TEXT NOT NULL DEFAULT '',
                    legacy_prompts INTEGER NOT NULL DEFAULT 0,
                    onboarded INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
                """
            )
            await db.execute(
                """
                INSERT INTO users (email, password_hash, owner_name)
                VALUES ('jon@kore.local', 'x', 'Jon')
                """
            )
            await db.commit()
        accounts = AccountStore(db_path)
        await accounts.init()
        user = await accounts.get_by_email("jon@kore.local")
        assert user is not None
        assert user.allowed is True
        assert user.paid_until is None
        off = await accounts.set_allowed("jon@kore.local", False)
        assert off is not None and off.allowed is False


def test_migrate_allowed_column():
    asyncio.run(_migrate_old_users_table())


async def _flag_gate() -> None:
    old = (
        settings.console_secret,
        settings.storage_db_path,
        settings.vault_root,
        settings.pilot_allowlist,
    )
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        settings.console_secret = "test-console-secret-32chars-xxxx"
        settings.storage_db_path = str(root / "kore.db")
        settings.vault_root = str(root / "vault")
        settings.pilot_allowlist = "eve@example.com"
        try:
            accounts = AccountStore(str(root / "accounts.db"))
            await accounts.init()
            homes = Homes(accounts)
            app = FastAPI()
            app.include_router(console_api_router)
            app.state.accounts = accounts
            app.state.homes = homes
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                created = await ac.post(
                    "/api/register",
                    json={"email": "eve@example.com", "password": "password1"},
                )
                assert created.status_code == 200, created.text
                assert created.json()["user"]["email"] == "eve@example.com"

                await ac.post("/api/logout")
                off = await accounts.set_allowed("eve@example.com", False)
                assert off is not None and off.allowed is False

                denied = await ac.post(
                    "/api/login",
                    json={"email": "eve@example.com", "password": "password1"},
                )
                assert denied.status_code == 403
                assert denied.json()["detail"] == "account_disabled"

                await accounts.set_allowed("eve@example.com", True)
                ok = await ac.post(
                    "/api/login",
                    json={"email": "eve@example.com", "password": "password1"},
                )
                assert ok.status_code == 200, ok.text
                assert COOKIE_NAME in ac.cookies or ok.cookies.get(COOKIE_NAME)

                await accounts.set_allowed("eve@example.com", False)
                me = await ac.get("/api/me")
                assert me.status_code == 401
                tasks = await ac.get("/api/tasks")
                assert tasks.status_code == 401
        finally:
            (
                settings.console_secret,
                settings.storage_db_path,
                settings.vault_root,
                settings.pilot_allowlist,
            ) = old


def test_disabled_account_cannot_login_or_use_session():
    asyncio.run(_flag_gate())
