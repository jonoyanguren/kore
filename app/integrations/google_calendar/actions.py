"""Day actions on calendar events: to-task + prep brief."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import openai

from app.llm.llm_assistant import resolve_model
from app.storage.memory import MemoryStore
from app.storage.task_tools import find_task_collision, sync_tasks_vault
from app.storage.vault import Vault

logger = logging.getLogger(__name__)

TASK_SYSTEM = """Eres Jone. A partir de un evento de calendario, propones UNA tarea útil para Jon.

Responde SOLO un JSON (sin markdown):
{"title":"...","project":"personal|kore|kimay|lol|... o null","notes":"una línea opcional"}

Reglas:
- title: acción clara ligada al evento (< 80 chars, español). Ej. "Prep call X", "Enviar follow-up Y".
- Si el evento ya es la acción (p.ej. "Dentista"), title tipo "Ir a Dentista" o prep concreta.
- project: slug si se deduce; si no, null.
- notes: hora + contexto mínimo; no inventes asistentes que no vengan en el texto."""

PREP_SYSTEM = """Eres Jone, companion de Jon. Preparas un brief corto ANTES de una reunión/cita.

Responde en español, texto plano (sin markdown, sin ** ni #), con esta estructura:

Prep
- (3–6 bullets: qué tener listo, preguntas, riesgos, contexto útil)

Objetivo
(una frase: para qué va Jon a esta cita)

Reglas:
- Usa SOLO el evento + memoria/diario que te pasen. No inventes gente ni hechos.
- Si hay poco contexto, dilo y da prep genérica útil (agenda, notas, siguiente paso).
- Corto: que se lea en 20 segundos."""


def _event_user_block(event: dict[str, Any]) -> str:
    title = str(event.get("title") or "(sin título)").strip()
    starts = str(event.get("starts_at") or "").strip()
    ends = str(event.get("ends_at") or "").strip()
    link = str(event.get("html_link") or "").strip()
    cal = str(event.get("calendar") or "").strip()
    source = str(event.get("source") or "").strip()
    lines = [
        f"Título: {title}",
        f"Empieza: {starts}",
    ]
    if ends:
        lines.append(f"Termina: {ends}")
    if cal:
        lines.append(f"Calendario: {cal}")
    if source:
        lines.append(f"Fuente: {source}")
    if link:
        lines.append(f"Link: {link}")
    return "\n".join(lines)


def _fallback_task(event: dict[str, Any]) -> dict[str, Any]:
    title = str(event.get("title") or "Evento").strip() or "Evento"
    if not title.lower().startswith(("prep", "ir a", "llamar", "enviar")):
        title = f"Prep: {title}"
    title = title[:120]
    starts = str(event.get("starts_at") or "").strip()
    notes = f"Calendario · {starts}".strip(" ·")
    return {"title": title, "project": None, "notes": notes}


async def propose_task_from_event(
    llm: openai.AsyncOpenAI,
    event: dict[str, Any],
) -> dict[str, Any]:
    try:
        response = await llm.chat.completions.create(
            model=resolve_model(strong=True),
            messages=[
                {"role": "system", "content": TASK_SYSTEM},
                {"role": "user", "content": _event_user_block(event)},
            ],
            max_tokens=300,
            temperature=0.2,
        )
        content = (response.choices[0].message.content or "").strip()
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\s*", "", content)
            content = re.sub(r"\s*```$", "", content)
        data = json.loads(content)
        title = str(data.get("title") or "").strip()
        if not title:
            return _fallback_task(event)
        project = data.get("project")
        project = (str(project).strip().lower() if project else None) or None
        notes = str(data.get("notes") or "").strip() or None
        return {"title": title[:120], "project": project, "notes": notes}
    except Exception:
        logger.exception("propose_task_from_event LLM failed; fallback")
        return _fallback_task(event)


async def create_task_from_event(
    *,
    llm: openai.AsyncOpenAI,
    memory: MemoryStore,
    vault: Vault,
    event: dict[str, Any],
) -> dict[str, Any]:
    title_raw = str(event.get("title") or "").strip()
    starts = str(event.get("starts_at") or "").strip()
    if not title_raw and not starts:
        return {"ok": False, "error": "event_required"}

    proposal = await propose_task_from_event(llm, event)
    title = proposal["title"]
    collision = await find_task_collision(memory, vault, title)
    if collision:
        if starts and starts[:16] not in title:
            title = f"{title} ({starts[:16]})"[:120]
            collision = await find_task_collision(memory, vault, title)
        if collision:
            return {"ok": False, "error": "duplicate", "detail": collision}

    due_at = starts[:16] if starts else None
    # All-day → date only is fine for due_at
    if starts and "T" not in starts:
        due_at = starts[:10]

    notes = proposal.get("notes") or ""
    link = str(event.get("html_link") or "").strip() or None
    if link and link not in notes:
        notes = f"{notes}\n{link}".strip() if notes else link

    task_id = await memory.add_task(
        title=title,
        notes=notes or None,
        url=link,
        project=proposal.get("project"),
        due_at=due_at,
        status="open",
    )
    await sync_tasks_vault(memory, vault)
    task = await memory.get_task(task_id)
    assert task is not None
    return {
        "ok": True,
        "task": {
            "id": task.id,
            "title": task.title,
            "status": task.status,
            "project": task.project,
            "url": task.url,
            "notes": task.notes,
            "due_at": task.due_at,
            "priority": task.priority,
        },
        "event": {
            "id": event.get("id"),
            "title": title_raw,
            "starts_at": starts,
        },
    }


async def prep_for_event(
    *,
    llm: openai.AsyncOpenAI,
    memory: MemoryStore,
    vault: Vault,
    event: dict[str, Any],
) -> dict[str, Any]:
    # Light context: memory digests + diary today
    digests = await memory.memory_digests(limit_per_category=6)
    mem_lines: list[str] = []
    for cat, items in digests.items():
        for _i, text in items[:4]:
            mem_lines.append(f"[{cat}] {text}")
    mem_block = "\n".join(mem_lines[:20]) if mem_lines else "(sin memoria)"

    diary = await memory.list_diary_for_day()
    diary_block = (
        "\n".join(f"- {t}" for _i, t in diary[:8]) if diary else "(vacío)"
    )

    done = ""
    if vault is not None:
        done = vault.read_done_tasks_excerpt(max_chars=800) or ""

    user = (
        f"{_event_user_block(event)}\n\n"
        f"=== MEMORIA ===\n{mem_block}\n\n"
        f"=== DIARIO HOY ===\n{diary_block}\n"
    )
    if done:
        user += f"\n=== DONE (excerpt) ===\n{done}\n"

    try:
        response = await llm.chat.completions.create(
            model=resolve_model(strong=True),
            messages=[
                {"role": "system", "content": PREP_SYSTEM},
                {"role": "user", "content": user},
            ],
            max_tokens=700,
            temperature=0.3,
        )
        text = (response.choices[0].message.content or "").strip()
    except Exception:
        logger.exception("prep_for_event LLM failed")
        title = str(event.get("title") or "la cita").strip()
        text = (
            f"Prep\n"
            f"- Revisar objetivo de «{title}»\n"
            f"- Anotar 2–3 preguntas\n"
            f"- Tener a mano links/notas relacionadas\n\n"
            f"Objetivo\n"
            f"Salir con un siguiente paso claro."
        )

    if not text:
        return {"ok": False, "error": "empty_prep"}
    return {
        "ok": True,
        "prep": text,
        "event": {
            "id": event.get("id"),
            "title": event.get("title"),
            "starts_at": event.get("starts_at"),
            "html_link": event.get("html_link"),
        },
    }
