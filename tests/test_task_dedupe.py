"""Task dedupe: don't recreate open or archived titles."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from app.storage.memory import MemoryStore
from app.storage.task_tools import build_task_tools, find_task_collision
from app.storage.vault import Vault


def test_list_done_task_titles_parses_archive():
    with tempfile.TemporaryDirectory() as tmp:
        vault = Vault(Path(tmp) / "vault")
        vault.ensure()
        path = vault.root / "tasks" / "done.md"
        path.write_text(
            "# tasks / done\n\n"
            "## 2026-07-27\n\n"
            "13. Mirar este reel de Instagram\n"
            "   hecha\n\n"
            "8. Añadir estados y proyecto en tareas\n"
            "   hecha\n",
            encoding="utf-8",
        )
        titles = vault.list_done_task_titles()
        assert any("reel" in t.lower() for t in titles)
        assert any("estados" in t.lower() for t in titles)


def test_add_task_refuses_archived_and_open_duplicates():
    async def _run():
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = Vault(root / "vault")
            vault.ensure()
            store = MemoryStore(str(root / "kore.db"))
            await store.init()

            await store.add_task("Reservar masajista en Santander")
            vault.append_done_tasks(
                "2026-07-27",
                ["8. Añadir estados y proyecto en tareas\n   hecha"],
            )

            _schemas, handlers = build_task_tools(store, vault)
            assert "archivada" in (
                await find_task_collision(
                    store, vault, "Añadir estados y proyecto en tareas Kore"
                )
                or ""
            ).lower() or "done.md" in (
                await find_task_collision(
                    store, vault, "Añadir estados y proyecto en tareas Kore"
                )
                or ""
            ).lower()

            blocked = await handlers["add_task"](
                {"title": "Añadir estados y proyecto"}
            )
            assert "No creada" in blocked

            dup_open = await handlers["add_task"](
                {"title": "Reservar masajista Santander miércoles"}
            )
            assert "No creada" in dup_open
            assert "ya existe" in dup_open.lower()

            ok = await handlers["add_task"]({"title": "Algo totalmente nuevo xyz"})
            assert ok.startswith("Creada")

    asyncio.run(_run())


def test_dream_capture_tools_exclude_add_task():
    from app.kernel.review_common import (
        DREAM_CAPTURE_TOOL_NAMES,
        build_capture_tools,
    )

    async def _run():
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = Vault(root / "vault")
            vault.ensure()
            store = MemoryStore(str(root / "kore.db"))
            await store.init()
            schemas, handlers = build_capture_tools(
                store, vault, allow=DREAM_CAPTURE_TOOL_NAMES
            )
            names = {s["function"]["name"] for s in schemas}
            assert "add_task" not in names
            assert "add_task" not in handlers
            assert "save_memory" in handlers

    asyncio.run(_run())
