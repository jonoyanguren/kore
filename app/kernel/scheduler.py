"""Morning dream schedule — in-process asyncio loop (+ optional HTTP trigger)."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

import openai

from app.config import settings
from app.integrations.gmail.client import GmailClient
from app.kernel.dream import run_dream
from app.kernel.review_common import is_blank_report
from app.storage.memory import MemoryStore
from app.storage.vault import Vault
from app.telegram.client import TelegramClient
from app.timeutil import MADRID, now_madrid, today_madrid

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


def needs_dream_consolidate(
    vault: Vault,
    target: str,
    last_run: str | None,
    last_status: str | None,
) -> bool:
    """True if yesterday's dream is missing, failed, or only a blank placeholder."""
    if last_run != target or last_status != "ok":
        return True
    body = dream_body_from_vault(vault.read_dream(target))
    return is_blank_report(body)


def today_fire_at(
    now: datetime,
    *,
    hour: int,
    minute: int,
) -> datetime:
    """Today's fire instant in Europe/Madrid (naive inputs normalized to Madrid)."""
    if now.tzinfo is None:
        now = now.replace(tzinfo=MADRID)
    else:
        now = now.astimezone(MADRID)
    return now.replace(hour=hour, minute=minute, second=0, microsecond=0)


def next_fire_at(
    now: datetime,
    *,
    hour: int,
    minute: int,
) -> datetime:
    """Next fire at hour:minute Madrid (tomorrow if today's slot already passed)."""
    fire = today_fire_at(now, hour=hour, minute=minute)
    if now.tzinfo is None:
        now = now.replace(tzinfo=MADRID)
    else:
        now = now.astimezone(MADRID)
    if now >= fire:
        return fire + timedelta(days=1)
    return fire


async def sleep_until(target: datetime) -> None:
    """Sleep until `target` (Madrid-aware). Wakes in ≤30s chunks for clock skew."""
    if target.tzinfo is None:
        target = target.replace(tzinfo=MADRID)
    while True:
        delay = (target - now_madrid()).total_seconds()
        if delay <= 0:
            return
        await asyncio.sleep(min(delay, 30.0))


async def run_scheduled_dream(
    store: MemoryStore,
    vault: Vault,
    llm_client: openai.AsyncOpenAI,
    telegram: TelegramClient,
    *,
    gmail: GmailClient | None = None,
) -> dict[str, str | bool]:
    """Consolidate yesterday once; deliver morning briefing once per Madrid day.

    Idempotent consolidate: if dream job already ok for yesterday, reuse vault file.
    Idempotent notify: job `dream_morning` keyed by today's Madrid date.
    """
    target = (today_madrid() - timedelta(days=1)).isoformat()
    morning = today_madrid().isoformat()
    chat_id = settings.telegram_allowed_chat_id

    last_run, last_status, _err = await store.get_job(JOB_DREAM)
    if not needs_dream_consolidate(vault, target, last_run, last_status):
        logger.info("Cron dream skip consolidate — already ok for day=%s", target)
        summary = dream_body_from_vault(vault.read_dream(target)) or (
            f"El sueño de {target} ya estaba consolidado."
        )
        consolidate_status = "skipped"
        error = ""
    else:
        if last_run == target and last_status == "ok":
            logger.warning(
                "Cron dream re-consolidate — vault blank/placeholder for day=%s",
                target,
            )
        logger.info("Cron dream starting for day=%s", target)
        summary = await run_dream(
            store,
            vault,
            llm_client,
            day=target,
            telegram=telegram,
            chat_id=chat_id,
            notify=False,
            gmail=gmail,
        )
        _last, status, err = await store.get_job(JOB_DREAM)
        consolidate_status = status or "unknown"
        error = err or ""
        # Don't mark morning "ok" if consolidate failed — allow catch-up retry.
        if consolidate_status != "ok" or is_blank_report(
            dream_body_from_vault(vault.read_dream(target))
        ):
            return {
                "status": consolidate_status,
                "day": target,
                "morning": morning,
                "notified": False,
                "telegram": settings.dream_notify_telegram,
                "error": error or "dream consolidate failed or blank",
                "preview": summary[:200],
            }

    last_m, status_m, _ = await store.get_job(JOB_MORNING)
    already_notified = last_m == morning and status_m == "ok"
    notified = False
    if already_notified:
        logger.info("Cron dream morning notify skip — already ok for %s", morning)
    elif not settings.dream_notify_telegram:
        # UI-first: mark morning done without Telegram (vista Día reads vault).
        await store.mark_job(JOB_MORNING, status="ok", ran_at=morning, error=None)
        logger.info(
            "Cron dream morning ready for UI (Telegram notify off) morning=%s",
            morning,
        )
        notified = False
    elif chat_id is not None:
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

    return {
        "status": consolidate_status,
        "day": target,
        "morning": morning,
        "notified": notified,
        "telegram": settings.dream_notify_telegram,
        "error": error,
        "preview": summary[:200],
    }


async def dream_cron_loop(
    store: MemoryStore,
    vault: Vault,
    llm_client: openai.AsyncOpenAI,
    telegram: TelegramClient,
    *,
    gmail: GmailClient | None = None,
    hour: int | None = None,
    minute: int | None = None,
) -> None:
    """Fire `run_scheduled_dream` every day at hour:minute Europe/Madrid.

    Catch-up: if the process starts after today's fire and morning notify
    has not run yet, fire immediately then wait until tomorrow.
    """
    hour = settings.dream_cron_hour if hour is None else hour
    minute = settings.dream_cron_minute if minute is None else minute
    logger.info(
        "Dream cron loop started — daily %02d:%02d Europe/Madrid",
        hour,
        minute,
    )
    while True:
        try:
            now = now_madrid()
            fire_today = today_fire_at(now, hour=hour, minute=minute)
            morning = today_madrid().isoformat()
            last_m, status_m, _ = await store.get_job(JOB_MORNING)
            done_today = last_m == morning and status_m == "ok"
            if done_today:
                # Prior bug: morning ok + vault "(vacío)" — still need catch-up.
                target = (today_madrid() - timedelta(days=1)).isoformat()
                last_d, status_d, _ = await store.get_job(JOB_DREAM)
                if needs_dream_consolidate(vault, target, last_d, status_d):
                    logger.warning(
                        "Dream cron morning marked ok but vault blank — re-fire morning=%s",
                        morning,
                    )
                    done_today = False

            if now >= fire_today and not done_today:
                logger.info(
                    "Dream cron firing (on-time or catch-up) morning=%s", morning
                )
                await run_scheduled_dream(
                    store, vault, llm_client, telegram, gmail=gmail
                )
                await sleep_until(fire_today + timedelta(days=1))
            elif now < fire_today:
                logger.info("Dream cron sleeping until %s", fire_today.isoformat())
                await sleep_until(fire_today)
            else:
                nxt = fire_today + timedelta(days=1)
                logger.info(
                    "Dream cron already done today — sleep until %s", nxt.isoformat()
                )
                await sleep_until(nxt)
        except asyncio.CancelledError:
            logger.info("Dream cron loop cancelled")
            raise
        except Exception:
            logger.exception("Dream cron loop error — retry in 60s")
            await asyncio.sleep(60)
