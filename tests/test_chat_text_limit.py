"""Chat accepts a pasted document; still 422s past the hard cap."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.storage.memory import MemoryStore
from app.storage.vault import Vault
from app.web.api import CHAT_TEXT_MAX, router as console_api_router


async def _run() -> None:
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

        class _FakeLLM:
            async def ask(self, user_text: str, **kwargs: object) -> str:
                stored = kwargs.get("persist_user_text")
                blob = stored if isinstance(stored, str) and stored else user_text
                await store.add_message("user", blob)
                reply = f"eco:{len(user_text)}"
                await store.add_message("assistant", reply)
                return reply

        app.state.llm = _FakeLLM()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            headers = {"Authorization": f"Bearer {secret}"}
            over_old_cap = "x" * 9000
            ok = await ac.post(
                "/api/chat", headers=headers, json={"text": over_old_cap}
            )
            assert ok.status_code == 200, ok.text
            assert ok.json()["reply"] == "eco:9000"

            stream = await ac.post(
                "/api/chat/stream",
                headers=headers,
                json={"text": over_old_cap},
            )
            assert stream.status_code == 200, stream.text

            too_big = "y" * (CHAT_TEXT_MAX + 1)
            rejected = await ac.post(
                "/api/chat", headers=headers, json={"text": too_big}
            )
            assert rejected.status_code == 422

            rejected_stream = await ac.post(
                "/api/chat/stream",
                headers=headers,
                json={"text": too_big},
            )
            assert rejected_stream.status_code == 422


def test_chat_accepts_long_paste_and_rejects_over_cap():
    asyncio.run(_run())
