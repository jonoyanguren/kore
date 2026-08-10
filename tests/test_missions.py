"""Missions store + vault + task runner (plan + tasks mocked)."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock

from app.kernel import mission_runner
from app.kernel.mission_plan import MissionPlan, MissionTask
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
                quality="pro",
                status="queued",
                next_run_at=now_madrid().replace(microsecond=0).isoformat(),
                max_ticks=1,
                tick_seconds=5,
            )
            row = await store.get_mission(mid)
            assert row is not None
            assert row.title == "Casas Cantabria"
            assert row.quality == "pro"
            path = vault.write_mission(mid, f"# {row.title}\n\nhola\n")
            assert path.is_file()
            assert "hola" in (vault.read_mission(mid) or "")

    asyncio.run(_run())


def test_mission_plan_then_tasks_to_done(monkeypatch):
    sample_plan = MissionPlan(
        tasks=[
            MissionTask(title="T1", goal="g1"),
            MissionTask(title="T2", goal="g2"),
        ]
    )

    async def fake_plan(llm, *, title, brief, usage_acc=None, **kwargs):
        return sample_plan

    async def fake_execute(llm, mission, plan, task_index, usage_acc, store=None):
        task = plan.tasks[task_index]
        return f"## {task.title}\n\nHecho {task_index + 1}.\n"

    async def fake_handoff(llm, **kwargs):
        return "Handoff breve para la siguiente."

    async def fake_summary(llm, **kwargs):
        return "## Resultado\n\n### Decisión\nStub listo.\n"

    async def fake_account_start(acc):
        return None

    async def fake_account_end(acc):
        return None

    monkeypatch.setattr(mission_runner, "plan_mission", fake_plan)
    monkeypatch.setattr(mission_runner, "_execute_task", fake_execute)
    monkeypatch.setattr(mission_runner, "generate_handoff", fake_handoff)
    monkeypatch.setattr(mission_runner, "generate_mission_summary", fake_summary)
    monkeypatch.setattr(mission_runner, "_maybe_snapshot_account_start", fake_account_start)
    monkeypatch.setattr(mission_runner, "_maybe_snapshot_account_end", fake_account_end)

    async def _run() -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "kore.db")
            store = MemoryStore(db)
            await store.init()
            vault = Vault(Path(tmp) / "vault")
            mid = await store.add_mission(
                "Stub",
                brief="probar tareas",
                status="queued",
                next_run_at=now_madrid().replace(microsecond=0).isoformat(),
                max_ticks=1,
                tick_seconds=5,
            )
            llm = AsyncMock()
            m = await store.get_mission(mid)
            assert m is not None

            await run_mission_tick(store, vault, m, llm)
            m = await store.get_mission(mid)
            assert m is not None
            assert m.max_ticks == 2
            assert m.status == "waiting"
            assert MissionPlan.from_json(m.plan_json) is not None

            await run_mission_tick(store, vault, m, llm)
            m = await store.get_mission(mid)
            assert m is not None
            assert m.step_index == 1
            assert m.status == "waiting"
            md = vault.read_mission(mid) or ""
            assert "Hecho 1" in md

            await run_mission_tick(store, vault, m, llm)
            m = await store.get_mission(mid)
            assert m is not None
            assert m.status == "done"
            assert m.step_index == 2
            md = vault.read_mission(mid) or ""
            assert "Hecho 2" in md
            assert "## Plan" in md
            assert "## Resultado" in md
            assert "Stub listo" in md
            plan = MissionPlan.from_json(m.plan_json)
            assert plan is not None
            assert "Resultado" in plan.summary

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
