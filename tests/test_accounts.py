"""Isolated per-user homes: register, no shared SQLite."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.accounts.homes import Homes
from app.accounts.store import AccountStore
from app.config import settings
from app.storage.memory import MemoryStore
from app.storage.vault import Vault
from app.web.api import router as console_api_router
from app.web.auth import COOKIE_NAME


def _app(accounts: AccountStore, homes: Homes) -> FastAPI:
    app = FastAPI()
    app.include_router(console_api_router)
    app.state.accounts = accounts
    app.state.homes = homes
    return app


async def _isolation():
    secret = "test-console-secret-32chars-xxxx"
    old = (
        settings.console_secret,
        settings.storage_db_path,
        settings.vault_root,
    )
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        settings.console_secret = secret
        settings.storage_db_path = str(root / "kore.db")
        settings.vault_root = str(root / "vault")
        try:
            accounts = AccountStore(str(root / "accounts.db"))
            await accounts.init()
            homes = Homes(accounts)
            app = _app(accounts, homes)
            transport = ASGITransport(app=app)
            async with (
                AsyncClient(transport=transport, base_url="http://test") as a,
                AsyncClient(transport=transport, base_url="http://test") as b,
            ):
                ra = await a.post(
                    "/api/register",
                    json={
                        "email": "ana@example.com",
                        "password": "password1",
                        "owner_name": "Ana",
                    },
                )
                assert ra.status_code == 200, ra.text
                assert ra.json()["user"]["email"] == "ana@example.com"
                assert ra.json()["user"]["onboarded"] is False

                rb = await b.post(
                    "/api/register",
                    json={
                        "email": "bob@example.com",
                        "password": "password2",
                        "owner_name": "Bob",
                    },
                )
                assert rb.status_code == 200, rb.text

                dup = await a.post(
                    "/api/register",
                    json={
                        "email": "ana@example.com",
                        "password": "password1",
                    },
                )
                assert dup.status_code == 400

                created = await a.post("/api/tasks", json={"title": "solo de ana"})
                assert created.status_code == 200
                listed_b = await b.get("/api/tasks", params={"status": "open"})
                assert listed_b.status_code == 200
                titles = [t["title"] for t in listed_b.json()["tasks"]]
                assert "solo de ana" not in titles

                listed_a = await a.get("/api/tasks", params={"status": "open"})
                titles_a = [t["title"] for t in listed_a.json()["tasks"]]
                assert "solo de ana" in titles_a

                me = await a.get("/api/me")
                assert me.json()["user"]["owner_name"] == "Ana"

                saved = await a.put(
                    "/api/me/companion",
                    json={
                        "owner_name": "Ana",
                        "companion_name": "Mara",
                        "companion_tone": "Directo y breve, sin relleno.",
                    },
                )
                assert saved.status_code == 200
                assert saved.json()["user"]["onboarded"] is True
                assert saved.json()["user"]["companion_name"] == "Mara"

                out = await a.post("/api/logout")
                assert out.status_code == 200
                assert COOKIE_NAME not in a.cookies or not a.cookies.get(COOKIE_NAME)
                me_out = await a.get("/api/me")
                assert me_out.status_code == 401

                login = await b.post(
                    "/api/logout",
                )
                assert login.status_code == 200
                again = await b.post(
                    "/api/login",
                    json={"email": "bob@example.com", "password": "password2"},
                )
                assert again.status_code == 200
                assert again.json()["user"]["email"] == "bob@example.com"
        finally:
            settings.console_secret, settings.storage_db_path, settings.vault_root = old


async def _bootstrap_legacy():
    secret = "bootstrap-secret-ok"
    old = (
        settings.console_secret,
        settings.storage_db_path,
        settings.vault_root,
        settings.owner_email,
    )
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        db = root / "kore.db"
        vault_dir = root / "vault"
        settings.console_secret = secret
        settings.storage_db_path = str(db)
        settings.vault_root = str(vault_dir)
        settings.owner_email = "jon@kore.local"
        try:
            store = MemoryStore(str(db))
            await store.init()
            await store.add_task(title="tarea legacy")
            vault = Vault(vault_dir)
            vault.ensure()
            (vault_dir / "hello.md").write_text("hi", encoding="utf-8")

            accounts = AccountStore(str(root / "accounts.db"))
            await accounts.init()
            homes = Homes(accounts)
            user = await homes.bootstrap_legacy()
            assert user is not None
            assert user.legacy_prompts is True
            assert not db.exists()
            home = await homes.open(user.id)
            rows = await home.memory.list_tasks(status="all")
            assert any(r.title == "tarea legacy" for r in rows)
            assert (home.vault.root / "hello.md").is_file()

            app = _app(accounts, homes)
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                login = await ac.post(
                    "/api/login",
                    json={"email": "jon@kore.local", "password": secret},
                )
                assert login.status_code == 200
                assert login.json()["user"]["legacy"] is True
                tasks = await ac.get("/api/tasks", params={"status": "open"})
                titles = [t["title"] for t in tasks.json()["tasks"]]
                assert "tarea legacy" in titles
        finally:
            (
                settings.console_secret,
                settings.storage_db_path,
                settings.vault_root,
                settings.owner_email,
            ) = old


def test_register_homes_are_isolated():
    asyncio.run(_isolation())


def test_bootstrap_moves_legacy_home():
    asyncio.run(_bootstrap_legacy())
