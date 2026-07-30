"""In-process mission runner: plan → tasks with handoffs (D21/D22)."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

import openai

from app.integrations.web.tools import build_web_tools
from app.kernel.mission_plan import (
    MissionPlan,
    apply_usage_to_plan,
    generate_handoff,
    plan_mission,
    render_mission_markdown,
)
from app.kernel.review_common import is_blank_report, looks_like_tool_markup, run_tool_loop
from app.llm.mission_quality import resolve_mission_model
from app.llm.openrouter_credits import fetch_usage
from app.llm.usage_cost import UsageAccumulator, format_cost_usd
from app.storage.memory import MemoryStore, MissionRow
from app.storage.vault import Vault
from app.timeutil import now_madrid

logger = logging.getLogger(__name__)

POLL_SECONDS = 5
TICK_GAP_SECONDS = 8

MISSION_SYSTEM = """Eres Jone, assistant de investigación de Jon.

Trabajas UNA tarea concreta de una misión en background. Escribes SOLO markdown útil en español.

Reglas:
- Usa web_search y fetch_url vía la API de tools (no escribas XML ni tool_calls en el texto).
- No inventes precios ni URLs. Si no hay dato sólido, dilo.
- Cita fuentes con links markdown: [nombre](https://…).
- Cuando ayude (producto, casa, sitio, UI, mapa, foto de referencia): incluye 1–3 imágenes
  con markdown ![descripción corta](https://url-directa).
  Solo URLs https reales a imagen (jpg/png/webp/gif o CDN). Sácalas de search/fetch
  (og:image, img src). Si no tienes URL real, no inventes ni pongas placeholder.
- Cumple SOLO el objetivo de esta tarea; no adelantes otras.
- Tono: claro, accionable, sin relleno.
- La respuesta final = markdown empezando por ## título de la tarea.
- No digas que eres una IA ni menciones ticks internos."""

MISSION_TASK_SYNTH_NUDGE = (
    "STOP. No llames más tools ni escribas XML. "
    "Con el contexto de este turno, escribe YA el entregable de la tarea "
    "en markdown en español (empieza por ##). Datos concretos, links e imágenes "
    "reales si aportan. Sin tool_calls, sin DSML, sin inventar."
)


def _iso(dt) -> str:
    return dt.replace(microsecond=0).isoformat()


def _load_plan(mission: MissionRow) -> MissionPlan | None:
    return MissionPlan.from_json(mission.plan_json)


def _usage_from_plan(plan: MissionPlan | None) -> UsageAccumulator:
    acc = UsageAccumulator()
    if plan is not None and plan.cost is not None:
        acc.cost = plan.cost
    return acc


async def _maybe_snapshot_account_start(acc: UsageAccumulator) -> None:
    if acc.cost.account_start_usd is not None:
        return
    snap = await fetch_usage(force=True)
    if snap is not None:
        acc.set_account_start(snap.usage_usd)


async def _maybe_snapshot_account_end(acc: UsageAccumulator) -> None:
    snap = await fetch_usage(force=True)
    if snap is not None:
        acc.set_account_end(snap.usage_usd)


def _status_line(mission: MissionRow, plan: MissionPlan, *, phase: str) -> str:
    n = len(plan.tasks)
    done = plan.completed_count()
    if phase == "planning":
        return "Estado: planificando tareas…"
    if phase == "running":
        idx = min(mission.step_index, n - 1) if n else 0
        task = plan.tasks[idx]
        return f"Estado: tarea {idx + 1}/{n} · {task.title}"
    if phase == "done":
        base = f"Estado: hecho · {n} tareas"
        if plan.cost and plan.cost.usd > 0:
            base += f" · {format_cost_usd(plan.cost.usd, estimated=plan.cost.estimated)}"
        return base
    return f"Estado: en curso · {done}/{n} tareas"


async def _run_planning(
    llm: openai.AsyncOpenAI,
    mission: MissionRow,
    usage_acc: UsageAccumulator,
    store: MemoryStore,
) -> MissionPlan:
    plan = await plan_mission(
        llm,
        title=mission.title,
        brief=mission.brief,
        quality=mission.quality,
        usage_acc=usage_acc,
        spend_store=store,
        spend_ref=f"mission:{mission.id}",
    )
    for t in plan.tasks:
        t.status = "pending"
    return plan


async def _execute_task(
    llm: openai.AsyncOpenAI,
    mission: MissionRow,
    plan: MissionPlan,
    task_index: int,
    usage_acc: UsageAccumulator,
    store: MemoryStore,
) -> str:
    task = plan.tasks[task_index]
    n = len(plan.tasks)
    handoff = (plan.handoff or "").strip()
    if task_index == 0:
        ctx = "(Primera tarea — sin handoff previo.)"
    else:
        ctx = handoff or "(Sin handoff previo.)"

    user = (
        f"MISIÓN — TAREA {task_index + 1}/{n}: {task.title}\n\n"
        f"Título misión: {mission.title}\n"
        f"Encargo original:\n{mission.brief}\n\n"
        f"Handoff de la tarea anterior:\n{ctx}\n\n"
        f"Objetivo de ESTA tarea:\n{task.goal}\n\n"
        f"Ejecuta esta tarea con búsqueda web. "
        f"Respuesta = SOLO markdown empezando por:\n"
        f"## {task.title}\n"
        f"(contenido con datos concretos, links e imágenes reales si aportan; "
        f"cierra la sección completa)"
    )

    tools, handlers = build_web_tools()
    model = resolve_mission_model(mission.quality)
    logger.info(
        "Mission %s task %s/%s model=%s title=%r",
        mission.id,
        task_index + 1,
        n,
        model,
        task.title[:50],
    )
    text = await run_tool_loop(
        llm,
        system=MISSION_SYSTEM,
        user_payload=user,
        tools=tools,
        handlers=handlers,
        model=model,
        max_tokens=5500,
        session_id=f"mission-{mission.id}-task-{task_index + 1}",
        usage_acc=usage_acc,
        synth_nudge=MISSION_TASK_SYNTH_NUDGE,
        spend_store=store,
        spend_kind="mission",
        spend_ref=f"mission:{mission.id}",
    )
    if is_blank_report(text) or looks_like_tool_markup(text):
        raise RuntimeError(f"Tarea vacía o inválida: {task.title}")
    t = text.strip()
    heading = f"## {task.title}"
    if not t.startswith("##"):
        t = f"{heading}\n\n{t}"
    elif not t.startswith(heading):
        t = f"{heading}\n\n{t.lstrip('#').strip()}"
    return t


async def run_mission_tick(
    store: MemoryStore,
    vault: Vault,
    mission: MissionRow,
    llm: openai.AsyncOpenAI,
) -> None:
    running = await store.count_missions_in_status("running")
    if running and mission.status != "running":
        later = _iso(now_madrid() + timedelta(seconds=TICK_GAP_SECONDS))
        await store.update_mission(mission.id, status="waiting", next_run_at=later)
        await store.add_mission_event(mission.id, "deferred", "max_1_active")
        return

    await store.update_mission(mission.id, status="running", clear_error=True)

    plan = _load_plan(mission)
    usage_acc = _usage_from_plan(plan)

    if plan is None:
        await store.add_mission_event(mission.id, "plan_start", None)
        await _maybe_snapshot_account_start(usage_acc)
        try:
            plan = await _run_planning(llm, mission, usage_acc, store)
            apply_usage_to_plan(plan, usage_acc)
            plan_json = plan.to_json()
            n = len(plan.tasks)
            md = render_mission_markdown(
                mission.title,
                mission.brief,
                plan,
                status_line=_status_line(mission, plan, phase="planning"),
                current_index=0,
            )
            path = vault.write_mission(mission.id, md)
            rel = (
                str(path.relative_to(vault.root))
                if path.is_relative_to(vault.root)
                else str(path)
            )
            nxt = _iso(now_madrid() + timedelta(seconds=TICK_GAP_SECONDS))
            await store.update_mission(
                mission.id,
                plan_json=plan_json,
                max_ticks=n,
                step_index=0,
                status="waiting",
                next_run_at=nxt,
                result_path=rel,
            )
            await store.add_mission_event(mission.id, "plan_done", f"tasks={n}")
            logger.info("Mission %s planned with %s tasks", mission.id, n)
        except Exception as exc:
            logger.exception("Mission %s planning failed", mission.id)
            await store.update_mission(
                mission.id,
                status="failed",
                error=str(exc)[:500],
                clear_next_run=True,
            )
            await store.add_mission_event(mission.id, "failed", f"plan:{exc}"[:300])
            vault.write_mission(
                mission.id,
                f"# {mission.title}\n\n> Estado: falló (plan)\n\n## Error\n\n{exc}\n",
            )
        return

    task_index = mission.step_index
    n = len(plan.tasks)

    if task_index >= n:
        await store.update_mission(
            mission.id,
            status="done",
            clear_next_run=True,
            clear_error=True,
        )
        await store.add_mission_event(mission.id, "done", f"tasks={n}")
        return

    task = plan.tasks[task_index]
    task.status = "running"
    await store.add_mission_event(
        mission.id, "task_start", f"{task_index + 1}/{n}:{task.title[:80]}"
    )

    try:
        output = await _execute_task(llm, mission, plan, task_index, usage_acc, store)
        task.output = output
        task.status = "done"

        if task_index + 1 < n:
            plan.handoff = await generate_handoff(
                llm,
                title=mission.title,
                brief=mission.brief,
                completed_task=task,
                next_task=plan.tasks[task_index + 1],
                mission_id=mission.id,
                quality=mission.quality,
                usage_acc=usage_acc,
                spend_store=store,
            )
        else:
            plan.handoff = ""

        apply_usage_to_plan(plan, usage_acc)
        next_index = task_index + 1
        is_done = next_index >= n
        if is_done:
            await _maybe_snapshot_account_end(usage_acc)
            apply_usage_to_plan(plan, usage_acc)
        md = render_mission_markdown(
            mission.title,
            mission.brief,
            plan,
            status_line=_status_line(
                mission,
                plan,
                phase="done" if is_done else "running",
            ),
            current_index=None if is_done else next_index,
        )
        path = vault.write_mission(mission.id, md)
        rel = (
            str(path.relative_to(vault.root))
            if path.is_relative_to(vault.root)
            else str(path)
        )

        if is_done:
            await store.update_mission(
                mission.id,
                status="done",
                step_index=next_index,
                plan_json=plan.to_json(),
                result_path=rel,
                clear_next_run=True,
                clear_error=True,
            )
            await store.add_mission_event(
                mission.id,
                "done",
                f"tasks={n}; usd={plan.cost.usd if plan.cost else 0:.4f}",
            )
            logger.info("Mission %s done after %s tasks", mission.id, n)
            return

        nxt = _iso(now_madrid() + timedelta(seconds=TICK_GAP_SECONDS))
        await store.update_mission(
            mission.id,
            status="waiting",
            step_index=next_index,
            plan_json=plan.to_json(),
            result_path=rel,
            next_run_at=nxt,
        )
        await store.add_mission_event(
            mission.id,
            "task_done",
            f"{task_index + 1}/{n}; next={nxt}",
        )
        logger.info(
            "Mission %s task %s/%s done; next %s",
            mission.id,
            task_index + 1,
            n,
            nxt,
        )
    except Exception as exc:
        logger.exception("Mission %s task %s failed", mission.id, task_index + 1)
        task.status = "failed"
        apply_usage_to_plan(plan, usage_acc)
        await store.update_mission(
            mission.id,
            status="failed",
            plan_json=plan.to_json(),
            error=str(exc)[:500],
            clear_next_run=True,
        )
        await store.add_mission_event(
            mission.id, "failed", f"task:{task_index + 1}:{exc}"[:300]
        )
        vault.write_mission(
            mission.id,
            render_mission_markdown(
                mission.title,
                mission.brief,
                plan,
                status_line=f"Estado: falló en tarea {task_index + 1}/{n}",
                current_index=task_index,
            )
            + f"\n## Error\n\n{exc}\n",
        )


async def mission_runner_loop(
    store: MemoryStore,
    vault: Vault,
    llm: openai.AsyncOpenAI,
) -> None:
    logger.info("Mission runner started (poll=%ss, tasks=on)", POLL_SECONDS)
    while True:
        try:
            now = _iso(now_madrid())
            due = await store.list_due_missions(now_iso=now, limit=1)
            if due:
                await run_mission_tick(store, vault, due[0], llm)
            await asyncio.sleep(POLL_SECONDS)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Mission runner error; retry in 15s")
            await asyncio.sleep(15)
