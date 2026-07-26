"""Lightweight Europe/Madrid cron without extra deps (poll every 60s)."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

import openai

from app.config import settings
from app.kernel.dream import run_dream
from app.storage.memory import MemoryStore
from app.storage.vault import Vault
from app.telegram.client import TelegramClient
from app.timeutil import now_madrid, today_madrid

logger = logging.getLogger(__name__)

# Dream window: 03:00–03:01 Madrid
DREAM_HOUR = 3
DREAM_MINUTE_END = 2
POLL_SECONDS = 60


async def scheduler_loop(
    store: MemoryStore,
    vault: Vault,
    llm_client: openai.AsyncOpenAI,
    telegram: TelegramClient,
) -> None:
    logger.info("Scheduler started (dream at %02d:00 Europe/Madrid)", DREAM_HOUR)
    while True:
        try:
            await _tick(store, vault, llm_client, telegram)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Scheduler tick failed")
        await asyncio.sleep(POLL_SECONDS)


async def _tick(
    store: MemoryStore,
    vault: Vault,
    llm_client: openai.AsyncOpenAI,
    telegram: TelegramClient,
) -> None:
    now = now_madrid()
    if now.hour != DREAM_HOUR or now.minute >= DREAM_MINUTE_END:
        return

    # Consolidate yesterday; job key uses yesterday's date as last_run_at
    target = (today_madrid() - timedelta(days=1)).isoformat()
    last_run, last_status, _err = await store.get_job("dream")
    if last_run == target and last_status == "ok":
        return

    logger.info("Cron dream starting for day=%s", target)
    await run_dream(
        store,
        vault,
        llm_client,
        day=target,
        telegram=telegram,
        chat_id=settings.telegram_allowed_chat_id,
        notify=True,
    )
