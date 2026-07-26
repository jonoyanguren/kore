"""Nightly (or manual) dream: consolidate diary + memory into vault/dreams."""

from __future__ import annotations

import logging
from datetime import timedelta

import openai

from app.config import settings
from app.storage.memory import MemoryStore
from app.storage.vault import Vault
from app.telegram.client import TelegramClient
from app.timeutil import today_madrid

logger = logging.getLogger(__name__)

DREAM_SYSTEM = """Eres el proceso de sueño de Jone (companion Kore).
Consolida el día del usuario en un informe corto en español, texto plano (sin markdown).
Estructura:
1) Resumen del día (3–6 líneas)
2) Hechos a recordar por categoría (solo si salen del diario/memoria reciente; no inventes)
3) Propuestas para mañana (tareas o agenda, 0–5 bullets)
4) Duplicados o ruido a ignorar (opcional, breve)

Sé concreto. Si el diario está vacío, dilo y usa solo memoria reciente.
No te presentes. No digas que eres un modelo."""


async def _llm_consolidate(client: openai.AsyncOpenAI, user_payload: str) -> str:
    response = await client.chat.completions.create(
        model=settings.openrouter_model,
        messages=[
            {"role": "system", "content": DREAM_SYSTEM},
            {"role": "user", "content": user_payload},
        ],
        max_tokens=min(settings.llm_max_tokens, 1500),
    )
    choice = response.choices[0].message
    return (choice.content or "").strip() or "(sueño vacío)"


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
    """Consolidate `day` (default: yesterday). Writes vault + marks job."""
    target = day or (today_madrid() - timedelta(days=1)).isoformat()

    diary = await store.list_diary_for_day(target)
    digests = await store.memory_digests(limit_per_category=12)
    open_tasks = await store.list_tasks(status="open", limit=20)
    agenda = await store.list_agenda_upcoming(from_day=target, limit=15)

    # Refresh vault exports from SQLite truth
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

    payload = (
        f"Día a consolidar: {target}\n\n"
        f"Diario:\n{diary_block}\n\n"
        f"Memoria reciente por categoría:\n{mem_block}\n\n"
        f"Tareas abiertas:\n{tasks_block}\n\n"
        f"Agenda próxima:\n{agenda_block}\n"
    )

    try:
        report = await _llm_consolidate(llm_client, payload)
        dream_path = vault.write_dream(
            target,
            f"# dream / {target}\n\n{report}\n",
        )
        await store.mark_job("dream", status="ok", ran_at=target, error=None)
        summary = (
            f"Sueño {target} guardado en {dream_path.name}.\n\n{report}"
        )
        logger.info("Dream ok for day=%s path=%s", target, dream_path)
    except Exception as exc:
        logger.exception("Dream failed for day=%s", target)
        await store.mark_job("dream", status="error", ran_at=target, error=str(exc))
        summary = f"El sueño de {target} falló: {exc}"

    if notify and telegram is not None and chat_id is not None:
        # Telegram hard limit ~4096; keep headroom
        text = summary if len(summary) < 3500 else summary[:3490] + "…"
        try:
            await telegram.send_message(chat_id, text)
        except Exception:
            logger.exception("Failed to send dream notify to chat_id=%s", chat_id)

    return summary
