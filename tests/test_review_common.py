"""Dream/review tool loop: blank replies get a synthesis pass."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.kernel.review_common import (
    is_blank_report,
    looks_like_tool_markup,
    run_tool_loop,
)


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


def test_looks_like_tool_markup():
    leak = (
        "## Rutas\n"
        "<｜｜DSML｜｜tool_calls>\n"
        '<｜｜DSML｜｜invoke name="web_search">\n'
        '<｜｜DSML｜｜parameter name="query">foo</｜｜DSML｜｜parameter>\n'
    )
    assert looks_like_tool_markup(leak)
    assert is_blank_report(leak)
    assert not looks_like_tool_markup("## Rutas\n- Lauterbrunnen con [link](https://x.com)")


def test_run_tool_loop_retries_when_tool_markup_leaks():
    async def _run():
        leak = (
            "Localizar rutas\n"
            "<｜｜DSML｜｜tool_calls>\n"
            '<｜｜DSML｜｜invoke name="web_search">\n'
            '<｜｜DSML｜｜parameter name="query">camping</｜｜DSML｜｜parameter>\n'
        )
        client = MagicMock()
        client.chat.completions.create = AsyncMock(
            side_effect=[
                _response(_msg(content=leak)),
                _response(
                    _msg(
                        content=(
                            "## Localizar rutas\n\n"
                            "- Grimsel Pass · camping en Innertkirchen\n"
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
                synth_nudge="escribe markdown",
            )

        assert "Grimsel" in text
        assert "tool_calls" not in text
        assert client.chat.completions.create.await_count == 2

    asyncio.run(_run())
