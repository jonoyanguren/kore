"""Morning dream: review the day's chat, fill gaps with tools, brief tomorrow/today."""

from __future__ import annotations

import logging
from datetime import date, timedelta

import openai

from app.integrations.gmail.client import GmailClient
from app.integrations.gmail.dream_inbox import fetch_inbox_block_for_dream
from app.kernel.review_common import (
    DREAM_CAPTURE_TOOL_NAMES,
    build_capture_tools,
    is_blank_report,
    run_tool_loop,
    transcript_block,
)
from app.llm.llm_assistant import resolve_model
from app.storage.memory import MemoryStore
from app.storage.vault import Vault
from app.telegram.client import TelegramClient
from app.timeutil import format_date_spoken, today_madrid

logger = logging.getLogger(__name__)

DREAM_SYSTEM = """Eres el proceso de sueño/briefing de Jone (companion Kore de Jon).
Trabajas en silencio: revisas el día y autogestionas la memoria.

Objetivo:
1) Leer TODO el chat del día a consolidar + diario/memoria/tareas/agenda ya guardados.
2) Rellenar huecos SOLO con: hechos durables → save_memory; eventos del día → add_diary_entry;
   citas → add_agenda_item. Puedes listar/actualizar/completar tareas YA existentes.
   NO crees tareas nuevas (no tienes add_task): si el chat menciona pendientes, menciónalos
   en el briefing; no reabras cosas de vault/tasks/done.md ni dupliques las abiertas.
3) Mira el bloque INBOX (Gmail unread): resume SOLO lo importante/accionable en la sección
   Inbox del mensaje final. Ignora newsletters y ruido. NO marques mails ni crees tareas
   desde el correo en este proceso.
4) Cuando hayas terminado de usar tools (o no haga falta ninguna), responde SOLO el mensaje
   final para Jon en español, texto plano (sin markdown, sin ** ni #).

Estructura del mensaje final (obligatoria), texto plano (sin markdown, sin ** ni #):

Resumen
(4–8 líneas concretas del día consolidado)

Tareas importantes
- (3–6 bullets; las que importan para HOY / el día siguiente al consolidado)
- Si no hay: Ninguna

Reuniones
- (hora — qué; de agenda o citas del chat)
- Si no hay: Ninguna

Inbox
- (3–6 bullets de correo importante / accionable para hoy)
- Si no hay nada relevante: Nada urgente

Ayuda
- (3–6 bullets: foco, riesgos, recordatorios útiles — NO repitas el listado de tareas)

Cierre
(una frase corta, tono directo)

Reglas: no digas que eres un modelo; no upsell; no pidas permiso; fechas naturales en el chat.
ISO solo dentro de las tools. Nunca inventes tareas nuevas en tools.
No inventes mails: solo lo del bloque INBOX."""


async def run_dream(
    store: MemoryStore,
    vault: Vault,
    llm_client: openai.AsyncOpenAI,
    *,
    day: str | None = None,
    telegram: TelegramClient | None = None,
    chat_id: int | None = None,
    notify: bool = True,
    gmail: GmailClient | None = None,
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
    inbox_block = await fetch_inbox_block_for_dream(gmail)

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
    from app.storage.memory import format_task_lines

    tasks_block = (
        "\n".join(format_task_lines(open_tasks, detailed=True))
        if open_tasks
        else "(ninguna)"
    )
    agenda_block = (
        "\n".join(f"- {starts} {title}" for _i, starts, title, _st in agenda)
        if agenda
        else "(nada)"
    )
    done_excerpt = vault.read_done_tasks_excerpt(max_chars=3500) or "(sin archivo)"

    spoken_target = format_date_spoken(target_date)
    spoken_next = format_date_spoken(date.fromisoformat(next_day))

    payload = (
        f"Día a consolidar (chat completo): {target} ({spoken_target})\n"
        f"Prep para el día siguiente: {next_day} ({spoken_next})\n\n"
        f"=== CHAT DEL DÍA ===\n{transcript_block(chat)}\n\n"
        f"=== DIARIO YA GUARDADO ===\n{diary_block}\n\n"
        f"=== MEMORIA (digests) ===\n{mem_block}\n\n"
        f"=== TAREAS ABIERTAS ===\n{tasks_block}\n\n"
        f"=== TAREAS ARCHIVADAS (done.md — NO reabrir) ===\n{done_excerpt}\n\n"
        f"=== AGENDA PRÓXIMA ===\n{agenda_block}\n\n"
        f"=== INBOX (Gmail unread) ===\n{inbox_block}\n\n"
        "Usa tools solo para huecos de memoria/diario/agenda. "
        "NO crees tareas nuevas. "
        "Luego escribe el mensaje final con las secciones "
        "Resumen / Tareas importantes / Reuniones / Inbox / Ayuda / Cierre."
    )

    tools, handlers = build_capture_tools(
        store, vault, allow=DREAM_CAPTURE_TOOL_NAMES
    )
    # Dream is once/day + heavy context: use strong model. DeepSeek V4 Pro
    # (thinking) has returned blank `content` on this path (~37s → "(vacío)").
    dream_model = resolve_model(strong=True)
    logger.info("Dream using model=%s for day=%s", dream_model, target)

    try:
        report = await run_tool_loop(
            llm_client,
            system=DREAM_SYSTEM,
            user_payload=payload,
            tools=tools,
            handlers=handlers,
            model=dream_model,
        )
        if is_blank_report(report):
            raise RuntimeError(
                "El modelo devolvió un dream vacío (sin secciones de briefing)"
            )
        dream_path = vault.write_dream(
            target,
            f"# dream / {target}\n\n{report}\n",
        )
        await store.mark_job("dream", status="ok", ran_at=target, error=None)
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
