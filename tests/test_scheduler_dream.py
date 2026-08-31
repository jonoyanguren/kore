"""Scheduled dream: consolidate once + morning notify once."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.kernel.review_common import is_blank_report
from app.kernel.scheduler import (
    dream_body_from_vault,
    needs_dream_consolidate,
    run_scheduled_dream,
)


def test_dream_body_from_vault_strips_header():
    raw = "# dream / 2026-07-26\n\nResumen\nHola\n"
    assert dream_body_from_vault(raw) == "Resumen\nHola"
    assert dream_body_from_vault(None) is None
    assert dream_body_from_vault("solo texto") == "solo texto"


def test_is_blank_report():
    assert is_blank_report(None)
    assert is_blank_report("")
    assert is_blank_report("  ")
    assert is_blank_report("(vacío)")
    assert is_blank_report("(sin respuesta)")
    assert not is_blank_report("Resumen\nHola")


def test_is_usable_dream():
    from app.kernel.review_common import is_usable_dream

    assert not is_usable_dream("(vacío)")
    assert not is_usable_dream("Briefing listo")
    assert is_usable_dream(
        "Resumen\nDía ok.\n\nTareas importantes\n- Ninguna\n\nCierre\nListo."
    )


def test_needs_dream_consolidate_retries_blank_vault():
    vault = MagicMock()
    vault.read_dream.return_value = "# dream / 2026-07-27\n\n(vacío)\n"
    assert needs_dream_consolidate(vault, "2026-07-27", "2026-07-27", "ok") is True

    vault.read_dream.return_value = (
        "# dream / 2026-07-27\n\nResumen\nBien\n\nAyuda\n- Foco\n\nCierre\nOk\n"
    )
    assert needs_dream_consolidate(vault, "2026-07-27", "2026-07-27", "ok") is False
    assert needs_dream_consolidate(vault, "2026-07-27", None, None) is True


def _cap_ok(store: MagicMock) -> None:
    store.summarize_llm_spend = AsyncMock(
        return_value={"usd": 0, "prompt_tokens": 0, "completion_tokens": 0, "calls": 0}
    )


def test_scheduled_dream_skips_consolidate_but_notifies():
    async def _run():
        store = MagicMock()
        _cap_ok(store)
        store.get_job = AsyncMock(
            side_effect=[
                ("2026-07-26", "ok", None),  # dream already done
                (None, None, None),  # dream_morning not yet
            ]
        )
        store.mark_job = AsyncMock()
        vault = MagicMock()
        vault.read_dream.return_value = (
            "# dream / 2026-07-26\n\n"
            "Resumen\nBriefing listo\n\n"
            "Ayuda\n- Revisa el Día\n\n"
            "Cierre\nOk\n"
        )
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
        _cap_ok(store)
        store.get_job = AsyncMock(
            side_effect=[
                ("2026-07-26", "ok", None),
                ("2026-07-27", "ok", None),  # already notified today
            ]
        )
        store.mark_job = AsyncMock()
        vault = MagicMock()
        vault.read_dream.return_value = (
            "# dream / 2026-07-26\n\n"
            "Resumen\nYa consolidado\n\n"
            "Ayuda\n- Ok\n\n"
            "Cierre\nx\n"
        )
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


def test_scheduled_dream_reconsolidates_blank_placeholder():
    async def _run():
        store = MagicMock()
        _cap_ok(store)
        # dream job "ok" but vault is the blank placeholder from DeepSeek empty reply
        store.get_job = AsyncMock(
            side_effect=[
                ("2026-07-26", "ok", None),
                ("2026-07-26", "ok", None),  # after run_dream
                ("2026-07-27", "ok", None),  # morning already marked
            ]
        )
        store.mark_job = AsyncMock()
        vault = MagicMock()
        vault.read_dream.side_effect = [
            "# dream / 2026-07-26\n\n(vacío)\n",  # needs_dream_consolidate
            "# dream / 2026-07-26\n\nResumen\nOK\n\nAyuda\n- x\n\nCierre\ny\n",
        ]
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
            settings.dream_notify_telegram = False
            run.return_value = "Resumen\nOK\n\nAyuda\n- x\n\nCierre\ny"

            result = await run_scheduled_dream(store, vault, MagicMock(), telegram)

        assert result["status"] == "ok"
        run.assert_awaited_once()
        assert result["notified"] is False

    asyncio.run(_run())
