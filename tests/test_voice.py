"""User voice profile: parse, prose, tools."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from app.accounts.context import bind_tenant, clear_tenant
from app.accounts.store import AccountStore
from app.accounts.voice import parse_voice, reply_system_for, voice_from_dict
from app.accounts.voice_tools import build_voice_tools
from app.storage.memory import MemoryStore
from app.storage.vault import Vault


def test_parse_structured_and_legacy():
    raw = voice_from_dict(
        {
            "address": "usted",
            "length": "telegrafico",
            "warmth": "cercano",
            "humor": "cero",
            "signoff": "saludo",
            "notes": "Nada de emojis",
        }
    ).to_storage()
    v = parse_voice(raw)
    assert v.structured is True
    assert v.address == "usted"
    assert v.length == "telegrafico"
    prose = v.to_prose("Ana")
    assert "usted" in prose.lower() or "Usted" in prose or "usted a Ana" in prose
    assert "Ana" in prose
    assert "Nada de emojis" in prose

    legacy = parse_voice("Directo y breve, sin relleno.")
    assert legacy.structured is False
    assert "Directo y breve" in legacy.notes


def test_reply_system_uses_owner():
    raw = voice_from_dict({"signoff": "nombre", "address": "tu"}).to_storage()
    sys = reply_system_for("Marta", raw)
    assert "Marta" in sys
    assert "Jon" not in sys or "EN SU NOMBRE" in sys
    assert "EN SU NOMBRE" in sys


async def _tool_run() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        accounts = AccountStore(str(root / "accounts.db"))
        await accounts.init()
        user = await accounts.create_user(
            email="ana@example.com",
            password="password1",
            owner_name="Ana",
            companion_name="Mara",
            companion_tone="Directo.",
            onboarded=True,
        )
        memory = MemoryStore(str(root / "kore.db"))
        await memory.init()
        await memory.add_message("user", "ok lo miro y te digo")
        await memory.add_message("assistant", "vale")
        await memory.add_message("user", "manda el pdf cuando puedas")
        vault = Vault(root / "vault")
        vault.ensure()
        bind_tenant(
            memory=memory,
            vault=vault,
            profile=user.profile(),
        )
        try:
            _schemas, handlers = build_voice_tools(accounts)
            chat = await handlers["list_recent_user_chat"]({"limit": 10})
            assert "ok lo miro" in chat
            assert "manda el pdf" in chat
            updated = await handlers["update_voice"](
                {"length": "telegrafico", "address": "tu"}
            )
            assert "guardado" in updated.lower() or "Telegráfico" in updated or "mínimas" in updated
            again = await accounts.get_user(user.id)
            assert again is not None
            parsed = parse_voice(again.companion_tone)
            assert parsed.structured is True
            assert parsed.length == "telegrafico"
            got = await handlers["get_voice"]({})
            assert "Ana" in got
        finally:
            clear_tenant()


def test_voice_tools_update_from_chat():
    asyncio.run(_tool_run())
