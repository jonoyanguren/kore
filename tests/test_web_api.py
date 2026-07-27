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

            tid_done = (
                await ac.post(
                    "/api/tasks",
                    headers={"Authorization": f"Bearer {secret}"},
                    json={"title": "ya hecha"},
                )
            ).json()["task"]["id"]
            await ac.post(
                f"/api/tasks/{tid_done}/complete",
                headers={"Authorization": f"Bearer {secret}"},
            )
            purged = await ac.delete(
                "/api/tasks/completed",
                headers={"Authorization": f"Bearer {secret}"},
            )
            assert purged.status_code == 200
            assert purged.json()["deleted"] >= 1
            assert purged.json().get("archived") is True
            assert await store.get_task(tid_done) is None
            done_md = (vault.root / "tasks" / "done.md").read_text(encoding="utf-8")
            assert "ya hecha" in done_md

            open_md = (vault.root / "tasks" / "open.md").read_text(encoding="utf-8")
            assert open_md.strip()

            class _FakeLLM:
                async def ask(self, user_text: str, **kwargs: object) -> str:
                    history = kwargs.get("persist_user_text")
                    stored = (
                        history if isinstance(history, str) and history else user_text
                    )
                    await store.add_message("user", stored)
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
            body = chat.json()
            assert body["reply"] == "eco:hola web"
            assert body.get("tasks_created") == []
            assert body.get("tasks_listed") == []
            msgs = await ac.get(
                "/api/messages",
                headers={"Authorization": f"Bearer {secret}"},
            )
            assert msgs.status_code == 200
            payload = msgs.json()["messages"]
            assert "has_more" in msgs.json()
            contents = [m["content"] for m in payload]
            assert "hola web" in contents
            assert "eco:hola web" in contents
            assert all("relative" in m or "created_at" in m for m in payload)

            # last-N: seed more than limit, expect newest kept
            for i in range(12):
                await store.add_message("user", f"m{i}")
            capped = await store.list_messages_for_day(limit=5)
            assert len(capped) == 5
            assert capped[0][1] == "m7"
            assert capped[-1][1] == "m11"

            recent = await store.list_recent_messages(limit=3)
            assert len(recent) == 3
            assert recent[-1][2] == "m11"

            page = await ac.get(
                "/api/messages?limit=3",
                headers={"Authorization": f"Bearer {secret}"},
            )
            assert page.status_code == 200
            assert page.json()["has_more"] is True
            oldest = page.json()["messages"][0]["id"]
            older = await ac.get(
                f"/api/messages?limit=3&before={oldest}",
                headers={"Authorization": f"Bearer {secret}"},
            )
            assert older.status_code == 200
            assert all(m["id"] < oldest for m in older.json()["messages"])

            tareas = await ac.post(
                "/api/chat",
                headers={"Authorization": f"Bearer {secret}"},
                json={"text": "/tareas"},
            )
            assert tareas.status_code == 200
            assert "Tareas" in tareas.json()["reply"]
            assert isinstance(tareas.json().get("tasks_listed"), list)

            # SSE chat stream (fast-path)
            stream = await ac.post(
                "/api/chat/stream",
                headers={"Authorization": f"Bearer {secret}"},
                json={"text": "/hora"},
            )
            assert stream.status_code == 200
            raw = stream.text
            assert "data:" in raw
            assert '"type": "done"' in raw or '"type":"done"' in raw

            day = await ac.get(
                "/api/day",
                headers={"Authorization": f"Bearer {secret}"},
            )
            assert day.status_code == 200
            snap = day.json()
            assert "clock" in snap and "headline" in snap
            assert "tasks" in snap and "agenda" in snap
            assert "briefing" in snap
            assert snap.get("greeting", "").startswith("Hola")
            assert "important_tasks" in snap["briefing"]
            assert "meetings" in snap["briefing"]
            assert "help" in snap["briefing"]

            mem = await ac.post(
                "/api/memory",
                headers={"Authorization": f"Bearer {secret}"},
                json={"category": "personal", "text": "le gusta el minimalismo"},
            )
            assert mem.status_code == 200
            mid = mem.json()["item"]["id"]
            listed = await ac.get(
                "/api/memory?category=personal",
                headers={"Authorization": f"Bearer {secret}"},
            )
            assert listed.status_code == 200
            assert any(i["id"] == mid for i in listed.json()["items"])
            diary = await ac.post(
                "/api/diary",
                headers={"Authorization": f"Bearer {secret}"},
                json={"text": "probando drawer"},
            )
            assert diary.status_code == 200
            did = diary.json()["entry"]["id"]
            dlist = await ac.get(
                "/api/diary",
                headers={"Authorization": f"Bearer {secret}"},
            )
            assert any(e["id"] == did for e in dlist.json()["entries"])
            assert (
                await ac.delete(
                    f"/api/diary/{did}",
                    headers={"Authorization": f"Bearer {secret}"},
                )
            ).status_code == 200
            assert (
                await ac.delete(
                    f"/api/memory/{mid}",
                    headers={"Authorization": f"Bearer {secret}"},
                )
            ).status_code == 200

            # Privacy: category wipe + overview + vault zip
            await ac.post(
                "/api/memory",
                headers={"Authorization": f"Bearer {secret}"},
                json={"category": "tmpwipe", "text": "borrar todo"},
            )
            await ac.post(
                "/api/memory",
                headers={"Authorization": f"Bearer {secret}"},
                json={"category": "tmpwipe", "text": "también esto"},
            )
            ov = await ac.get(
                "/api/privacy/overview",
                headers={"Authorization": f"Bearer {secret}"},
            )
            assert ov.status_code == 200
            assert ov.json()["memory_total"] >= 2
            wiped = await ac.delete(
                "/api/memory/category/tmpwipe",
                headers={"Authorization": f"Bearer {secret}"},
            )
            assert wiped.status_code == 200
            assert wiped.json()["deleted"] == 2
            assert not (vault.root / "memory" / "tmpwipe.md").exists()

            z = await ac.get(
                "/api/vault/export",
                headers={"Authorization": f"Bearer {secret}"},
            )
            assert z.status_code == 200
            assert z.headers["content-type"].startswith("application/zip")
            assert len(z.content) > 20


def test_web_api_auth_and_tasks():
    asyncio.run(_run())


def test_audio_format_from_mime():
    from app.llm.transcribe import audio_format_from_mime

    assert audio_format_from_mime("audio/webm;codecs=opus") == "webm"
    assert audio_format_from_mime("audio/ogg") == "ogg"
    assert audio_format_from_mime(None) == "webm"
