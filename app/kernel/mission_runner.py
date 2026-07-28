"""In-process mission runner: timed ticks with real web research (D21)."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

import openai

from app.integrations.web.tools import build_web_tools
from app.kernel.review_common import is_blank_report, run_tool_loop
from app.llm.llm_assistant import resolve_model
from app.storage.memory import MemoryStore, MissionRow
from app.storage.vault import Vault
from app.timeutil import now_madrid

logger = logging.getLogger(__name__)

POLL_SECONDS = 5
# Chain ticks quickly once a mission is running (research is the slow part).
TICK_GAP_SECONDS = 8

MISSION_SYSTEM = """Eres Jone, assistant de investigación de Jon.

Trabajas en una MISIÓN en background. Escribes SOLO markdown útil en español.

Reglas:
- Usa web_search y fetch_url para datos reales (precios, modelos, fuentes).
- No inventes precios ni URLs. Si no hay dato sólido, dilo.
- Cita fuentes con links.
- Tono: claro, accionable, sin relleno.
- No digas que eres una IA ni menciones "stub" o "tick interno"."""


def _iso(dt) -> str:
    return dt.replace(microsecond=0).isoformat()


def _shell_markdown(mission: MissionRow, *, status_line: str, body: str) -> str:
    return (
        f"# {mission.title}\n\n"
        f"> {status_line}\n\n"
        f"## Encargo\n\n"
        f"{mission.brief.strip() or '(sin brief)'}\n\n"
        f"{body.strip()}\n"
    )


async def _research_tick(
    llm: openai.AsyncOpenAI,
    mission: MissionRow,
    *,
    step: int,
    previous_md: str,
) -> str:
    tools, handlers = build_web_tools()
    is_final = step >= mission.max_ticks
    if is_final:
        user = (
            f"MISIÓN (tick final {step}/{mission.max_ticks}): sintetiza el INFORME FINAL.\n\n"
            f"Título: {mission.title}\n"
            f"Encargo:\n{mission.brief}\n\n"
            f"--- Markdown actual ---\n{previous_md[:12000]}\n\n"
            "Escribe el documento FINAL completo en markdown con:\n"
            "## Resumen\n"
            "## Hallazgos (con precios/datos concretos y links)\n"
            "## Opciones recomendadas (tabla o lista comparativa)\n"
            "## Riesgos / qué mirar\n"
            "## Siguiente paso\n"
            "Puedes hacer 1–2 búsquedas extras si falta un dato clave. "
            "Respuesta = SOLO el markdown del informe (empieza por # título)."
        )
    else:
        user = (
            f"MISIÓN (tick {step}/{mission.max_ticks}): investiga y actualiza el borrador.\n\n"
            f"Título: {mission.title}\n"
            f"Encargo:\n{mission.brief}\n\n"
            f"--- Markdown actual ---\n{previous_md[:8000] or '(vacío)'}\n\n"
            "Haz búsquedas web relevantes, lee 1–3 páginas útiles, y escribe un "
            "borrador markdown actualizado con:\n"
            "## Investigación\n"
            "### Fuentes\n"
            "### Notas / datos\n"
            "### Preguntas abiertas\n"
            "Respuesta = SOLO el markdown del borrador (puedes incluir # título)."
        )

    # Daily (DeepSeek) while dogfooding — Sonnet was ~$2+/mission with tool loops.
    # Revisit: strong on final tick only if quality needs it.
    model = resolve_model(strong=False)
    logger.info(
        "Mission %s tick %s/%s model=%s final=%s",
        mission.id,
        step,
        mission.max_ticks,
        model,
        is_final,
    )
    text = await run_tool_loop(
        llm,
        system=MISSION_SYSTEM,
        user_payload=user,
        tools=tools,
        handlers=handlers,
        model=model,
        max_tokens=3500,
        session_id=f"mission-{mission.id}-tick-{step}",
    )
    if is_blank_report(text):
        raise RuntimeError("El modelo devolvió informe vacío")
    # Ensure title heading exists
    t = text.strip()
    if not t.startswith("#"):
        t = f"# {mission.title}\n\n{t}"
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
    await store.add_mission_event(mission.id, "tick_start", f"step={mission.step_index}")

    step = mission.step_index + 1
    previous = vault.read_mission(mission.id) or _shell_markdown(
        mission,
        status_line=f"Estado: en curso · tick 0/{mission.max_ticks}",
        body="## Investigación\n\n_Arrancando…_\n",
    )

    try:
        content = await _research_tick(llm, mission, step=step, previous_md=previous)
        # Keep Encargo visible if model dropped it
        if "## Encargo" not in content and mission.brief.strip():
            content = _shell_markdown(
                mission,
                status_line=(
                    f"Estado: {'hecho' if step >= mission.max_ticks else 'en curso'} · "
                    f"tick {step}/{mission.max_ticks}"
                ),
                body=content.split("\n", 2)[-1] if content.startswith("#") else content,
            )
        else:
            # Refresh status line in blockquote if present
            lines = content.splitlines()
            for i, line in enumerate(lines[:8]):
                if line.startswith(">"):
                    lines[i] = (
                        f"> Estado: {'hecho' if step >= mission.max_ticks else 'en curso'} · "
                        f"tick {step}/{mission.max_ticks}"
                    )
                    content = "\n".join(lines)
                    break

        path = vault.write_mission(mission.id, content)
        rel = (
            str(path.relative_to(vault.root))
            if path.is_relative_to(vault.root)
            else str(path)
        )
    except Exception as exc:
        logger.exception("Mission %s tick failed", mission.id)
        await store.update_mission(
            mission.id,
            status="failed",
            error=str(exc)[:500],
            clear_next_run=True,
        )
        await store.add_mission_event(mission.id, "failed", str(exc)[:300])
        vault.write_mission(
            mission.id,
            _shell_markdown(
                mission,
                status_line="Estado: falló",
                body=f"## Error\n\n{exc}\n",
            ),
        )
        return

    if step >= mission.max_ticks:
        await store.update_mission(
            mission.id,
            status="done",
            step_index=step,
            result_path=rel,
            clear_next_run=True,
            clear_error=True,
        )
        await store.add_mission_event(mission.id, "done", f"ticks={step}")
        logger.info("Mission %s done after %s ticks", mission.id, step)
        return

    nxt = _iso(now_madrid() + timedelta(seconds=TICK_GAP_SECONDS))
    await store.update_mission(
        mission.id,
        status="waiting",
        step_index=step,
        result_path=rel,
        next_run_at=nxt,
    )
    await store.add_mission_event(mission.id, "tick_done", f"step={step}; next={nxt}")
    logger.info(
        "Mission %s tick %s/%s; next %s",
        mission.id,
        step,
        mission.max_ticks,
        nxt,
    )


async def mission_runner_loop(
    store: MemoryStore,
    vault: Vault,
    llm: openai.AsyncOpenAI,
) -> None:
    logger.info("Mission runner started (poll=%ss, research=on)", POLL_SECONDS)
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
