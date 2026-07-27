"""Phase 1: vault write-through, tasks, agenda."""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.storage.memory import MemoryStore
from app.storage.vault import Vault


async def _run():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        db = root / "kore.db"
        vault = Vault(root / "vault")
        vault.ensure()
        store = MemoryStore(str(db))
        await store.init()

        mid = await store.save_memory("work", "hablé con el equipo")
        vault.append_memory("work", mid, "hablé con el equipo")
        work_md = (vault.root / "memory" / "work.md").read_text(encoding="utf-8")
        assert "hablé con el equipo" in work_md

        did = await store.add_diary_entry("entrené 40min", day="2026-07-25")
        vault.append_diary("2026-07-25", did, "entrené 40min")
        diary_md = (vault.root / "diary" / "2026-07-25.md").read_text(encoding="utf-8")
        assert "entrené" in diary_md

        tid = await store.add_task(
            "comprar café",
            due_at="2026-07-27",
            priority=1,
            url="https://example.com/cafe",
            project="personal",
            notes="con leche",
        )
        rows = await store.list_tasks(status="open")
        assert any(r.id == tid for r in rows)
        got = await store.get_task(tid)
        assert got is not None
        assert got.url == "https://example.com/cafe"
        assert got.project == "personal"
        assert await store.update_task(tid, status="in_progress")
        assert (await store.get_task(tid)).status == "in_progress"
        assert await store.complete_task(tid)
        assert await store.list_tasks(status="open") == []
        tid2 = await store.add_task("borrarme")
        assert await store.delete_task(tid2)
        assert (await store.get_task(tid2)).status == "cancelled"

        from app.storage.memory import format_tasks_message

        sample = await store.add_task(
            "Mirar reel",
            url="https://instagram.com/reel/x",
            project="personal",
            due_at="2026-07-28",
        )
        msg = format_tasks_message([await store.get_task(sample)])
        assert f"{sample}." in msg
        assert "abierta" in msg
        assert "personal" in msg
        assert "instagram.com" in msg
        assert "[open]" not in msg

        aid = await store.add_agenda_item("dentista", "2026-07-28T10:00")
        upcoming = await store.list_agenda_upcoming(from_day="2026-07-26")
        assert any(r[0] == aid for r in upcoming)

        await store.mark_job("dream", status="ok", ran_at="2026-07-25")
        last, status, err = await store.get_job("dream")
        assert last == "2026-07-25" and status == "ok" and err is None

        vault.write_dream("2026-07-25", "# dream\n\nhola")
        assert (vault.root / "dreams" / "2026-07-25.md").is_file()

        await store.add_message("user", "hola dream", session_date="2026-07-25")
        await store.add_message("assistant", "hey", session_date="2026-07-25")
        msgs = await store.list_messages_for_day("2026-07-25")
        assert msgs == [("user", "hola dream"), ("assistant", "hey")]


def test_phase1_store_and_vault():
    import asyncio

    asyncio.run(_run())
