"""Dream/review tool loop: blank replies get a synthesis pass."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.kernel.review_common import is_blank_report, run_tool_loop


def _msg(*, content: str | None = None, tool_calls=None, reasoning: str | None = None):
    return SimpleNamespace(content=content, tool_calls=tool_calls, reasoning=reasoning)


def _response(message, *, finish_reason: str = "stop"):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=message, finish_reason=finish_reason)]
    )


def test_run_tool_loop_synthesizes_on_empty_first_reply():
    async def _run():
        client = MagicMock()
        client.chat.completions.create = AsyncMock(
            side_effect=[
                _response(_msg(content="")),  # blank final
                _response(
                    _msg(
                        content=(
                            "Resumen\nDía denso.\n\n"
                            "Tareas importantes\n- Ninguna\n\n"
                            "Reuniones\n- Ninguna\n\n"
                            "Ayuda\n- Revisa el Día\n\n"
                            "Cierre\nListo."
                        )
                    )
                ),
            ]
        )

        with patch("app.kernel.review_common.settings") as settings:
            settings.openrouter_model = "test/model"
            settings.llm_max_tokens = 2000
            text = await run_tool_loop(
                client,
                system="sys",
                user_payload="payload",
                tools=[],
                handlers={},
                model="test/strong",
            )

        assert not is_blank_report(text)
        assert "Resumen" in text
        assert client.chat.completions.create.await_count == 2
        assert (
            client.chat.completions.create.await_args_list[0].kwargs["model"]
            == "test/strong"
        )

    asyncio.run(_run())


def test_run_tool_loop_uses_reasoning_when_content_blank():
    async def _run():
        client = MagicMock()
        client.chat.completions.create = AsyncMock(
            return_value=_response(
                _msg(content="", reasoning="Resumen\nHabía datos.\n\nCierre\nOk.")
            )
        )

        with patch("app.kernel.review_common.settings") as settings:
            settings.openrouter_model = "test/model"
            settings.llm_max_tokens = 2000
            text = await run_tool_loop(
                client,
                system="sys",
                user_payload="payload",
                tools=[],
                handlers={},
            )

        assert "Había datos" in text
        assert client.chat.completions.create.await_count == 1

    asyncio.run(_run())
