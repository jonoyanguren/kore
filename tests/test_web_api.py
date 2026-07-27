"""Web console API: auth + tasks."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.storage.memory import MemoryStore
from app.storage.vault import Vault
from app.web.api import router as console_api_router


async def _run():
    secret = "test-console-secret-32chars-xxxx"
    settings.console_secret = secret

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        store = MemoryStore(str(root / "kore.db"))
        await store.init()
        vault = Vault(root / "vault")
        vault.ensure()

        app = FastAPI()
        app.include_router(console_api_router)
        app.state.memory = store
        app.state.vault = vault

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.get("/api/tasks")
            assert r.status_code == 401

            bad = await ac.post("/api/login", json={"secret": "nope"})
            assert bad.status_code == 401

            login = await ac.post("/api/login", json={"secret": secret})
            assert login.status_code == 200
            assert login.json() == {"ok": True}

            me = await ac.get("/api/me")
            assert me.status_code == 200

            created = await ac.post(
                "/api/tasks",
                json={
                    "title": "Meter consola",
                    "status": "in_progress",
                    "project": "kore",
                    "url": "https://example.com",
                },
            )
            assert created.status_code == 200
            task = created.json()["task"]
            tid = task["id"]
            assert task["title"] == "Meter consola"
            assert task["status"] == "in_progress"
            assert task["url"] == "https://example.com"

            listed = await ac.get("/api/tasks", params={"status": "open"})
            assert listed.status_code == 200
            ids = [t["id"] for t in listed.json()["tasks"]]
            assert tid in ids

            patched = await ac.patch(
                f"/api/tasks/{tid}",
                json={"status": "open", "title": "Meter consola web"},
            )
            assert patched.status_code == 200
            assert patched.json()["task"]["status"] == "open"
            assert patched.json()["task"]["title"] == "Meter consola web"

            ac.cookies.clear()
            bearer = await ac.get(
                "/api/tasks",
                headers={"Authorization": f"Bearer {secret}"},
            )
            assert bearer.status_code == 200

            done = await ac.post(
                f"/api/tasks/{tid}/complete",
                headers={"Authorization": f"Bearer {secret}"},
            )
            assert done.status_code == 200
            assert done.json()["task"]["status"] == "done"
            assert await store.list_tasks(status="open") == []

            tid2 = (
                await ac.post(
                    "/api/tasks",
                    headers={"Authorization": f"Bearer {secret}"},
                    json={"title": "borrar"},
                )
            ).json()["task"]["id"]
            deleted = await ac.delete(
                f"/api/tasks/{tid2}",
                headers={"Authorization": f"Bearer {secret}"},
            )
            assert deleted.status_code == 200
            assert (await store.get_task(tid2)).status == "cancelled"

            open_md = (vault.root / "tasks" / "open.md").read_text(encoding="utf-8")
            assert open_md.strip()

            class _FakeLLM:
                async def ask(self, user_text: str, **_kwargs: object) -> str:
                    await store.add_message("user", user_text)
                    reply = f"eco:{user_text}"
                    await store.add_message("assistant", reply)
                    return reply

            app.state.llm = _FakeLLM()
            chat = await ac.post(
                "/api/chat",
                headers={"Authorization": f"Bearer {secret}"},
                json={"text": "hola web"},
            )
            assert chat.status_code == 200
            assert chat.json()["reply"] == "eco:hola web"
            msgs = await ac.get(
                "/api/messages",
                headers={"Authorization": f"Bearer {secret}"},
            )
            assert msgs.status_code == 200
            contents = [m["content"] for m in msgs.json()["messages"]]
            assert "hola web" in contents
            assert "eco:hola web" in contents


def test_web_api_auth_and_tasks():
    asyncio.run(_run())
