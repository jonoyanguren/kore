"""LLM spend ledger store."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from app.storage.memory import MemoryStore


def test_llm_spend_insert_and_summarize():
    async def _run() -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = MemoryStore(str(Path(tmp) / "kore.db"))
            await store.init()
            await store.add_llm_spend(
                kind="chat",
                model="deepseek/deepseek-v4-pro",
                prompt_tokens=100,
                completion_tokens=50,
                usd=0.01,
                day="2026-07-29",
            )
            await store.add_llm_spend(
                kind="mission",
                model="deepseek/deepseek-v4-pro",
                prompt_tokens=200,
                completion_tokens=80,
                usd=0.05,
                estimated=True,
                ref="mission:1",
                day="2026-07-29",
            )
            await store.add_llm_spend(
                kind="dream",
                model="anthropic/claude-haiku-4.5",
                prompt_tokens=500,
                completion_tokens=200,
                usd=0.02,
                day="2026-07-28",
            )
            rows = await store.list_llm_spend(
                day_from="2026-07-28", day_to="2026-07-29"
            )
            assert len(rows) == 3
            summary = await store.summarize_llm_spend(
                day_from="2026-07-29", day_to="2026-07-29"
            )
            assert abs(summary["usd"] - 0.06) < 1e-6
            assert summary["calls"] == 2
            kinds = {k["kind"]: k["usd"] for k in summary["by_kind"]}
            assert abs(kinds["mission"] - 0.05) < 1e-6

    asyncio.run(_run())
