"""In-process mission runner: timed ticks, max 1 active (D21)."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from app.storage.memory import MemoryStore, MissionRow
from app.storage.vault import Vault
from app.timeutil import now_madrid

logger = logging.getLogger(__name__)

POLL_SECONDS = 5


def _iso(dt) -> str:
    return dt.replace(microsecond=0).isoformat()


def _initial_markdown(mission: MissionRow) -> str:
    return (
        f"# {mission.title}\n\n"
        f"> Estado: en curso · tick 0/{mission.max_ticks}\n\n"
        f"## Encargo\n\n"
        f"{mission.brief.strip() or '(sin brief)'}\n\n"
        f"## Progreso\n\n"
        f"_Arrancando…_\n"
    )


def _progress_markdown(mission: MissionRow, step: int, note: str) -> str:
    existing = ""
    # Rebuild a clean progressive report each tick (source of truth = DB + this write)
    lines = [
        f"# {mission.title}",
        "",
        f"> Estado: {'hecho' if step >= mission.max_ticks else 'en curso'} · "
        f"tick {step}/{mission.max_ticks}",
        "",
        "## Encargo",
        "",
        mission.brief.strip() or "(sin brief)",
        "",
        "## Progreso",
        "",
    ]
    for i in range(1, step + 1):
        lines.append(f"### Tick {i}")
        lines.append("")
        if i == step:
            lines.append(note)
        else:
            lines.append(f"Paso {i} completado.")
        lines.append("")
    if step >= mission.max_ticks:
        lines.extend(
            [
                "## Resultado",
                "",
                "Misión stub terminada. El runner real (research / tools) llegará en el "
                "siguiente slice; este archivo demuestra el flujo input → loop → output.",
                "",
            ]
        )
    return "\n".join(lines)


async def run_mission_tick(
    store: MemoryStore,
    vault: Vault,
    mission: MissionRow,
) -> None:
    """One tick for a due mission. Stub: append progress until max_ticks."""
    running = await store.count_missions_in_status("running")
    if running and mission.status != "running":
        # Another mission is mid-tick; defer
        later = _iso(now_madrid() + timedelta(seconds=max(5, mission.tick_seconds)))
        await store.update_mission(mission.id, status="waiting", next_run_at=later)
        await store.add_mission_event(mission.id, "deferred", "max_1_active")
        return

    await store.update_mission(mission.id, status="running", clear_error=True)
    await store.add_mission_event(mission.id, "tick_start", f"step={mission.step_index}")

    step = mission.step_index + 1
    note = (
        f"Tick stub #{step}: revisado el encargo y anotado progreso "
        f"(sin tools reales todavía)."
    )
    if mission.result_path is None or mission.step_index == 0:
        path = vault.write_mission(mission.id, _initial_markdown(mission))
        rel = str(path.relative_to(vault.root)) if path.is_relative_to(vault.root) else str(path)
        await store.update_mission(mission.id, result_path=rel)

    content = _progress_markdown(mission, step, note)
    path = vault.write_mission(mission.id, content)
    rel = str(path.relative_to(vault.root)) if path.is_relative_to(vault.root) else str(path)

    if step >= mission.max_ticks:
        await store.update_mission(
            mission.id,
            status="done",
            step_index=step,
            result_path=rel,
            clear_next_run=True,
        )
        await store.add_mission_event(mission.id, "done", f"ticks={step}")
        logger.info("Mission %s done after %s ticks", mission.id, step)
        return

    nxt = _iso(now_madrid() + timedelta(seconds=max(5, mission.tick_seconds)))
    await store.update_mission(
        mission.id,
        status="waiting",
        step_index=step,
        result_path=rel,
        next_run_at=nxt,
    )
    await store.add_mission_event(mission.id, "tick_done", f"step={step}; next={nxt}")
    logger.info("Mission %s tick %s/%s; next %s", mission.id, step, mission.max_ticks, nxt)


async def mission_runner_loop(store: MemoryStore, vault: Vault) -> None:
    logger.info("Mission runner started (poll=%ss)", POLL_SECONDS)
    while True:
        try:
            now = _iso(now_madrid())
            due = await store.list_due_missions(now_iso=now, limit=1)
            if due:
                await run_mission_tick(store, vault, due[0])
            await asyncio.sleep(POLL_SECONDS)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Mission runner error; retry in 15s")
            await asyncio.sleep(15)
