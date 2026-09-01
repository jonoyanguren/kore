"""Per-home monthly LLM cap."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.accounts.context import CompanionProfile, current_profile
from app.accounts.homes import Homes
from app.accounts.store import AccountStore
from app.config import settings
from app.llm.pilot_cap import cap_usd, is_blocked, status_for
from app.storage.memory import MemoryStore
from app.timeutil import session_date_str
from app.web.api import router as console_api_router


def test_status_unlimited_and_blocked():
    async def _run() -> None:
        old_cap = settings.pilot_llm_cap_usd
        with tempfile.TemporaryDirectory() as tmp:
            store = MemoryStore(str(Path(tmp) / "kore.db"))
            await store.init()
            today = session_date_str()
            await store.add_llm_spend(
                kind="chat",
                model="test",
                usd=5.0,
                day=today,
            )
            try:
                settings.pilot_llm_cap_usd = 0
                st = await status_for(store)
                assert st.unlimited is True
                assert st.blocked is False
                assert st.used_usd == 5.0

                settings.pilot_llm_cap_usd = 4.0
                st = await status_for(store)
                assert st.blocked is True
                assert st.remaining_usd == 0.0
                assert await is_blocked(store) is True

                settings.pilot_llm_cap_usd = 20.0
                st = await status_for(store)
                assert st.blocked is False
                assert abs(st.remaining_usd - 15.0) < 1e-6
            finally:
                settings.pilot_llm_cap_usd = old_cap

    asyncio.run(_run())
    assert cap_usd() >= 0


def test_legacy_profile_is_unlimited_even_with_plan_cap():
    token = current_profile.set(
        CompanionProfile(
            user_id=1,
            email="jon@kore.local",
            owner_name="Jon",
            companion_name="Jone",
            companion_tone="",
            legacy_prompts=True,
            onboarded=True,
            llm_cap_usd=3.0,
        )
    )
    try:
        assert cap_usd() == 0.0
    finally:
        current_profile.reset(token)


def test_per_user_zero_is_unlimited():
    token = current_profile.set(
        CompanionProfile(
            user_id=2,
            email="ana@example.com",
            owner_name="Ana",
            companion_name="Jone",
            companion_tone="",
            legacy_prompts=False,
            onboarded=True,
            llm_cap_usd=0.0,
        )
    )
    try:
        assert cap_usd() == 0.0
    finally:
        current_profile.reset(token)


async def _http_cap() -> None:
    old = (
        settings.console_secret,
        settings.storage_db_path,
        settings.vault_root,
        settings.pilot_llm_cap_usd,
    )
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        settings.console_secret = "test-console-secret-32chars-xxxx"
        settings.storage_db_path = str(root / "kore.db")
        settings.vault_root = str(root / "vault")
        settings.pilot_llm_cap_usd = 0.05
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
                user_id = created.json()["user"]["id"]
                home = await homes.open(user_id)
                await home.memory.add_llm_spend(
                    kind="chat",
                    model="test",
                    usd=0.10,
                    day=session_date_str(),
                )
                usage = await ac.get("/api/usage")
                assert usage.status_code == 200
                body = usage.json()["usage"]
                assert body["blocked"] is True
                assert body["source"] == "home"

                chat = await ac.post("/api/chat", json={"text": "hola"})
                assert chat.status_code == 402
                assert chat.json()["detail"] == "llm_cap"

                hora = await ac.post("/api/chat", json={"text": "/hora"})
                assert hora.status_code == 200
                assert "reply" in hora.json()

                mission = await ac.post(
                    "/api/missions",
                    json={"title": "x", "brief": "y", "launch": True},
                )
                assert mission.status_code == 402
        finally:
            (
                settings.console_secret,
                settings.storage_db_path,
                settings.vault_root,
                settings.pilot_llm_cap_usd,
            ) = old


def test_chat_and_mission_cut_at_cap():
    asyncio.run(_http_cap())
