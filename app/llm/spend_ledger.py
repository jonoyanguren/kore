"""Persist LLM completion costs into the llm_spend ledger."""

from __future__ import annotations

import logging
from typing import Any

from app.llm.usage_cost import parse_completion_usage
from app.storage.memory import MemoryStore

logger = logging.getLogger(__name__)


async def log_completion(
    store: MemoryStore | None,
    response: Any,
    *,
    model: str,
    kind: str,
    ref: str | None = None,
    session_id: str | None = None,
) -> None:
    """Best-effort insert of one completion into llm_spend."""
    if store is None:
        return
    event = parse_completion_usage(response, model=model)
    if event is None:
        return
    try:
        await store.add_llm_spend(
            kind=kind,
            model=model,
            prompt_tokens=event.prompt_tokens,
            completion_tokens=event.completion_tokens,
            usd=event.usd,
            estimated=event.estimated,
            ref=ref,
            session_id=session_id,
        )
    except Exception:
        logger.exception("Failed to log llm_spend kind=%s ref=%s", kind, ref)
