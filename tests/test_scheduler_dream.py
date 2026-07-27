"""Scheduled dream: consolidate once + morning notify once."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.kernel.scheduler import dream_body_from_vault, run_scheduled_dream


def test_dream_body_from_vault_strips_header():
    raw = "# dream / 2026-07-26\n\nResumen\nHola\n"
    assert dream_body_from_vault(raw) == "Resumen\nHola"
    assert dream_body_from_vault(None) is None
    assert dream_body_from_vault("solo texto") == "solo texto"


def test_scheduled_dream_skips_consolidate_but_notifies():
    async def _run():
        store = MagicMock()
        store.get_job = AsyncMock(
            side_effect=[
                ("2026-07-26", "ok", None),  # dream already done
                (None, None, None),  # dream_morning not yet
            ]
        )
        store.mark_job = AsyncMock()
        vault = MagicMock()
        vault.read_dream.return_value = "# dream / 2026-07-26\n\nBriefing listo\n"
        telegram = MagicMock()
        telegram.send_message = AsyncMock()
        llm = MagicMock()

        with (
            patch("app.kernel.scheduler.today_madrid") as today,
            patch("app.kernel.scheduler.settings") as settings,
            patch("app.kernel.scheduler.run_dream", new_callable=AsyncMock) as run,
        ):
            from datetime import date

            today.return_value = date(2026, 7, 27)
            settings.telegram_allowed_chat_id = 42
            settings.dream_notify_telegram = True

            result = await run_scheduled_dream(store, vault, llm, telegram)

        assert result["status"] == "skipped"
        assert result["day"] == "2026-07-26"
        assert result["notified"] is True
        run.assert_not_called()
        telegram.send_message.assert_awaited_once()
        assert "Briefing listo" in telegram.send_message.await_args.args[1]
        store.mark_job.assert_awaited()
        assert store.mark_job.await_args.args[0] == "dream_morning"

    asyncio.run(_run())


def test_scheduled_dream_no_double_morning_notify():
    async def _run():
        store = MagicMock()
        store.get_job = AsyncMock(
            side_effect=[
                ("2026-07-26", "ok", None),
                ("2026-07-27", "ok", None),  # already notified today
            ]
        )
        store.mark_job = AsyncMock()
        vault = MagicMock()
        vault.read_dream.return_value = "# dream / 2026-07-26\n\nx\n"
        telegram = MagicMock()
        telegram.send_message = AsyncMock()

        with (
            patch("app.kernel.scheduler.today_madrid") as today,
            patch("app.kernel.scheduler.settings") as settings,
            patch("app.kernel.scheduler.run_dream", new_callable=AsyncMock) as run,
        ):
            from datetime import date

            today.return_value = date(2026, 7, 27)
            settings.telegram_allowed_chat_id = 42
            settings.dream_notify_telegram = True

            result = await run_scheduled_dream(store, vault, MagicMock(), telegram)

        assert result["notified"] is False
        telegram.send_message.assert_not_called()
        run.assert_not_called()
        store.mark_job.assert_not_called()

    asyncio.run(_run())
