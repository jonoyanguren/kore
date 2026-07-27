"""Cron entrypoints — triggered by external schedule (GitHub Actions), not in-process polling."""

from __future__ import annotations

import logging
from datetime import timedelta

import openai

from app.config import settings
from app.kernel.dream import run_dream
from app.storage.memory import MemoryStore
from app.storage.vault import Vault
from app.telegram.client import TelegramClient
from app.timeutil import today_madrid

logger = logging.getLogger(__name__)

JOB_DREAM = "dream"
JOB_MORNING = "dream_morning"


def dream_body_from_vault(raw: str | None) -> str | None:
    """Strip the `# dream / …` vault header; return plain briefing text."""
    if not raw:
        return None
    lines = raw.splitlines()
    i = 0
    if lines and lines[0].lstrip().startswith("#"):
        i = 1
        while i < len(lines) and not lines[i].strip():
            i += 1
    body = "\n".join(lines[i:]).strip()
    return body or None


async def run_scheduled_dream(
    store: MemoryStore,
    vault: Vault,
    llm_client: openai.AsyncOpenAI,
    telegram: TelegramClient,
) -> dict[str, str | bool]:
    """Consolidate yesterday once; always deliver morning briefing once per Madrid day.

    Idempotent consolidate: if dream job already ok for yesterday, reuse vault file.
    Idempotent notify: job `dream_morning` keyed by today's Madrid date (covers dual
    CET/CEST GH Actions slots without double-sending).
    """
    target = (today_madrid() - timedelta(days=1)).isoformat()
    morning = today_madrid().isoformat()
    chat_id = settings.telegram_allowed_chat_id

    last_run, last_status, _err = await store.get_job(JOB_DREAM)
    if last_run == target and last_status == "ok":
        logger.info("Cron dream skip consolidate — already ok for day=%s", target)
        summary = dream_body_from_vault(vault.read_dream(target)) or (
            f"El sueño de {target} ya estaba consolidado."
        )
        consolidate_status = "skipped"
        error = ""
    else:
        logger.info("Cron dream starting for day=%s", target)
        # Scheduler owns Telegram delivery (once per morning).
        summary = await run_dream(
            store,
            vault,
            llm_client,
            day=target,
            telegram=telegram,
            chat_id=chat_id,
            notify=False,
        )
        _last, status, err = await store.get_job(JOB_DREAM)
        consolidate_status = status or "unknown"
        error = err or ""

    last_m, status_m, _ = await store.get_job(JOB_MORNING)
    already_notified = last_m == morning and status_m == "ok"
    notified = False
    if not already_notified and chat_id is not None:
        text = summary if len(summary) < 3500 else summary[:3490] + "…"
        try:
            await telegram.send_message(chat_id, text)
            await store.mark_job(JOB_MORNING, status="ok", ran_at=morning, error=None)
            notified = True
            logger.info("Cron dream morning notify sent for morning=%s", morning)
        except Exception as exc:
            logger.exception("Cron dream morning notify failed")
            await store.mark_job(
                JOB_MORNING, status="error", ran_at=morning, error=str(exc)
            )
            if not error:
                error = str(exc)
    elif already_notified:
        logger.info("Cron dream morning notify skip — already ok for %s", morning)

    return {
        "status": consolidate_status,
        "day": target,
        "morning": morning,
        "notified": notified,
        "error": error,
        "preview": summary[:200],
    }
