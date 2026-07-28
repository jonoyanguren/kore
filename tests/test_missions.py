"""Missions store + vault + stub tick (research mocked)."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock

from app.kernel import mission_runner
from app.kernel.mission_runner import run_mission_tick
from app.storage.memory import MemoryStore
from app.storage.vault import Vault
from app.timeutil import now_madrid


def test_mission_crud_and_vault():
    async def _run() -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "kore.db")
            store = MemoryStore(db)
            await store.init()
            vault = Vault(Path(tmp) / "vault")
            mid = await store.add_mission(
                "Casas Cantabria",
                brief="3 hab, cerca del mar",
                status="queued",
                next_run_at=now_madrid().replace(microsecond=0).isoformat(),
                max_ticks=2,
                tick_seconds=5,
            )
            row = await store.get_mission(mid)
            assert row is not None
            assert row.title == "Casas Cantabria"
            path = vault.write_mission(mid, f"# {row.title}\n\nhola\n")
            assert path.is_file()
            assert "hola" in (vault.read_mission(mid) or "")

    asyncio.run(_run())


def test_mission_ticks_to_done_with_fake_research(monkeypatch):
    async def fake_research(llm, mission, *, step, previous_md):
        return (
            f"# {mission.title}\n\n"
            f"> Estado: en curso · tick {step}/{mission.max_ticks}\n\n"
            f"## Encargo\n\n{mission.brief}\n\n"
            f"## Hallazgos\n\nDato fake tick {step}.\n"
        )

    monkeypatch.setattr(mission_runner, "_research_tick", fake_research)

    async def _run() -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "kore.db")
            store = MemoryStore(db)
            await store.init()
            vault = Vault(Path(tmp) / "vault")
            mid = await store.add_mission(
                "Stub",
                brief="probar ticks",
                status="queued",
                next_run_at=now_madrid().replace(microsecond=0).isoformat(),
                max_ticks=2,
                tick_seconds=5,
            )
            llm = AsyncMock()
            m = await store.get_mission(mid)
            assert m is not None
            await run_mission_tick(store, vault, m, llm)
            m = await store.get_mission(mid)
            assert m is not None
            assert m.step_index == 1
            assert m.status == "waiting"
            assert "Dato fake tick 1" in (vault.read_mission(mid) or "")
            await run_mission_tick(store, vault, m, llm)
            m = await store.get_mission(mid)
            assert m is not None
            assert m.status == "done"
            assert m.step_index == 2

    asyncio.run(_run())


def test_list_hides_done():
    async def _run() -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "kore.db")
            store = MemoryStore(db)
            await store.init()
            a = await store.add_mission("Activa", status="queued")
            b = await store.add_mission("Hecha", status="done")
            all_rows = await store.list_missions(include_done=True)
            active = await store.list_missions(include_done=False)
            ids_all = {r.id for r in all_rows}
            ids_active = {r.id for r in active}
            assert a in ids_all and b in ids_all
            assert a in ids_active and b not in ids_active

    asyncio.run(_run())
