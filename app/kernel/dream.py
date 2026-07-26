"""Morning dream: review the day's chat, fill gaps with tools, brief tomorrow/today."""

from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from typing import Any

import openai

from app.config import settings
from app.storage.memory import MemoryStore
from app.storage.task_tools import build_task_tools
from app.storage.tools import build_memory_tools
from app.storage.vault import Vault
from app.telegram.client import TelegramClient
from app.timeutil import format_date_spoken, today_madrid

logger = logging.getLogger(__name__)

MAX_DREAM_TOOL_ITERS = 10
MAX_TRANSCRIPT_CHARS = 40_000

DREAM_SYSTEM = """Eres el proceso de sueño/briefing de Jone (companion Kore de Jon).
Trabajas en silencio: revisas el día y autogestionas la memoria.

Objetivo:
1) Leer TODO el chat del día a consolidar + diario/memoria/tareas/agenda ya guardados.
2) Rellenar huecos con tools: hechos durables → save_memory; eventos del día → add_diary_entry;
   pendientes claros → add_task; citas → add_agenda_item. No inventes. No dupliques lo ya listado.
3) Cuando hayas terminado de usar tools (o no haga falta ninguna), responde SOLO el mensaje
   final para Jon en español, texto plano (sin markdown, sin ** ni #).

Estructura del mensaje final (obligatoria):
A) Resumen del día (4–8 líneas, concreto)
B) Huecos que acabo de anotar (si no hubo: "Nada nuevo que anotar.")
C) Prep de hoy (día siguiente al consolidado): foco, tareas abiertas relevantes, agenda;
   si creaste tareas/agenda para hoy, menciónalo. 3–8 líneas.
D) Una frase de cierre corta (tono directo, sin presentarte).

Reglas: no digas que eres un modelo; no upsell; no pidas permiso; fechas naturales en el chat.
ISO solo dentro de las tools."""


def _build_dream_tools(
    store: MemoryStore, vault: Vault
) -> tuple[list[dict], dict[str, Any]]:
    mem_schemas, mem_handlers = build_memory_tools(store, vault)
    task_schemas, task_handlers = build_task_tools(store, vault)
    # Only capture / planning tools — no ClickUp/LoL/project docs noise
    allow = {
        "save_memory",
        "add_diary_entry",
        "add_task",
        "complete_task",
        "list_tasks",
        "add_agenda_item",
        "list_agenda",
        "forget_memory",
    }
    schemas = [
        s for s in mem_schemas + task_schemas if s["function"]["name"] in allow
    ]
    handlers = {n: h for n, h in {**mem_handlers, **task_handlers}.items() if n in allow}
    return schemas, handlers


def _transcript_block(messages: list[tuple[str, str]]) -> str:
    if not messages:
        return "(sin mensajes de chat ese día)"
    lines = []
    for role, content in messages:
        label = "Jon" if role == "user" else "Jone"
        text = (content or "").strip()
        if not text:
            continue
        lines.append(f"{label}: {text}")
    blob = "\n".join(lines)
    if len(blob) > MAX_TRANSCRIPT_CHARS:
        blob = "…[transcript truncado]\n" + blob[-MAX_TRANSCRIPT_CHARS:]
    return blob


async def _execute_tool(
    handlers: dict[str, Any], tool_call: Any
) -> str:
    name = tool_call.function.name
    handler = handlers.get(name)
    if handler is None:
        return f"Herramienta desconocida: {name}"
    try:
        arguments = json.loads(tool_call.function.arguments or "{}")
    except json.JSONDecodeError:
        return f"No pude interpretar los argumentos para {name}."
    try:
        return await handler(arguments)
    except Exception:
        logger.exception("Dream tool %s failed", name)
        return f"La herramienta {name} falló."


async def _dream_llm_loop(
    client: openai.AsyncOpenAI,
    *,
    tools: list[dict],
    handlers: dict[str, Any],
    user_payload: str,
) -> str:
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": DREAM_SYSTEM},
        {"role": "user", "content": user_payload},
    ]
    final_text: str | None = None

    for _ in range(MAX_DREAM_TOOL_ITERS):
        response = await client.chat.completions.create(
            model=settings.openrouter_model,
            max_tokens=min(settings.llm_max_tokens, 2500),
            messages=messages,
            tools=tools or None,
        )
        message = response.choices[0].message
        tool_calls = message.tool_calls
        if not tool_calls:
            final_text = (message.content or "").strip() or "(sueño vacío)"
            break

        messages.append(
            {
                "role": "assistant",
                "content": message.content,
                "tool_calls": [tc.model_dump() for tc in tool_calls],
            }
        )
        for tool_call in tool_calls:
            result = await _execute_tool(handlers, tool_call)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                }
            )

    if final_text is None:
        final_text = (
            "El sueño se enredó con demasiadas tools. Prueba /dream otra vez."
        )
    return final_text


async def run_dream(
    store: MemoryStore,
    vault: Vault,
    llm_client: openai.AsyncOpenAI,
    *,
    day: str | None = None,
    telegram: TelegramClient | None = None,
    chat_id: int | None = None,
    notify: bool = True,
) -> str:
    """Consolidate chat+captures for `day` (default: yesterday). Brief next morning."""
    target = day or (today_madrid() - timedelta(days=1)).isoformat()
    target_date = date.fromisoformat(target)
    next_day = (target_date + timedelta(days=1)).isoformat()

    chat = await store.list_messages_for_day(target)
    diary = await store.list_diary_for_day(target)
    digests = await store.memory_digests(limit_per_category=12)
    open_tasks = await store.list_tasks(status="open", limit=25)
    agenda = await store.list_agenda_upcoming(from_day=target, limit=20)

    vault.rewrite_diary_day(target, diary)
    for category in await store.list_categories():
        items = await store.list_memory_all_by_category(category)
        vault.rewrite_memory_category(category, items)

    diary_block = (
        "\n".join(f"- {t}" for _i, t in diary) if diary else "(vacío)"
    )
    mem_lines: list[str] = []
    for cat, items in digests.items():
        mem_lines.append(f"[{cat}]")
        for _i, text in items:
            mem_lines.append(f"  - {text}")
    mem_block = "\n".join(mem_lines) if mem_lines else "(sin memoria)"
    tasks_block = (
        "\n".join(
            f"- (id {i}) {title}" + (f" due {due}" if due else "")
            for i, title, _st, due, _p in open_tasks
        )
        if open_tasks
        else "(ninguna)"
    )
    agenda_block = (
        "\n".join(f"- {starts} {title}" for _i, starts, title, _st in agenda)
        if agenda
        else "(nada)"
    )

    spoken_target = format_date_spoken(target_date)
    spoken_next = format_date_spoken(date.fromisoformat(next_day))

    payload = (
        f"Día a consolidar (chat completo): {target} ({spoken_target})\n"
        f"Prep para el día siguiente: {next_day} ({spoken_next})\n\n"
        f"=== CHAT DEL DÍA ===\n{_transcript_block(chat)}\n\n"
        f"=== DIARIO YA GUARDADO ===\n{diary_block}\n\n"
        f"=== MEMORIA (digests) ===\n{mem_block}\n\n"
        f"=== TAREAS ABIERTAS ===\n{tasks_block}\n\n"
        f"=== AGENDA PRÓXIMA ===\n{agenda_block}\n\n"
        "Usa tools para huecos del chat que no estén ya en diario/memoria/tareas. "
        "Luego escribe el mensaje final A–D."
    )

    tools, handlers = _build_dream_tools(store, vault)

    try:
        report = await _dream_llm_loop(
            llm_client, tools=tools, handlers=handlers, user_payload=payload
        )
        dream_path = vault.write_dream(
            target,
            f"# dream / {target}\n\n{report}\n",
        )
        await store.mark_job("dream", status="ok", ran_at=target, error=None)
        # User-facing: the report itself (no vault path noise)
        summary = report
        logger.info(
            "Dream ok for day=%s msgs=%d path=%s",
            target,
            len(chat),
            dream_path,
        )
    except Exception as exc:
        logger.exception("Dream failed for day=%s", target)
        await store.mark_job("dream", status="error", ran_at=target, error=str(exc))
        summary = f"El sueño de {target} falló: {exc}"

    if notify and telegram is not None and chat_id is not None:
        text = summary if len(summary) < 3500 else summary[:3490] + "…"
        try:
            await telegram.send_message(chat_id, text)
        except Exception:
            logger.exception("Failed to send dream notify to chat_id=%s", chat_id)

    return summary
