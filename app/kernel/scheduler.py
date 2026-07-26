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


async def run_scheduled_dream(
    store: MemoryStore,
    vault: Vault,
    llm_client: openai.AsyncOpenAI,
    telegram: TelegramClient,
) -> dict[str, str]:
    """Consolidate yesterday once. Idempotent if already ok for that day."""
    target = (today_madrid() - timedelta(days=1)).isoformat()
    last_run, last_status, _err = await store.get_job("dream")
    if last_run == target and last_status == "ok":
        logger.info("Cron dream skip — already ok for day=%s", target)
        return {"status": "skipped", "day": target, "reason": "already_ok"}

    logger.info("Cron dream starting for day=%s", target)
    summary = await run_dream(
        store,
        vault,
        llm_client,
        day=target,
        telegram=telegram,
        chat_id=settings.telegram_allowed_chat_id,
        notify=True,
    )
    _last, status, err = await store.get_job("dream")
    return {
        "status": status or "unknown",
        "day": target,
        "error": err or "",
        "preview": summary[:200],
    }
