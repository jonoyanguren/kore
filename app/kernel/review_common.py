"""Shared helpers for dream / close day reviews (transcript + capture tools + LLM loop)."""

from __future__ import annotations

import json
import logging
from typing import Any

import openai

from app.config import settings
from app.storage.memory import MemoryStore
from app.storage.task_tools import build_task_tools
from app.storage.tools import build_memory_tools
from app.storage.vault import Vault

logger = logging.getLogger(__name__)

MAX_TOOL_ITERS = 10
MAX_TRANSCRIPT_CHARS = 40_000

CAPTURE_TOOL_NAMES = {
    "save_memory",
    "add_diary_entry",
    "add_task",
    "complete_task",
    "list_tasks",
    "add_agenda_item",
    "list_agenda",
    "forget_memory",
}


def build_capture_tools(
    store: MemoryStore, vault: Vault
) -> tuple[list[dict], dict[str, Any]]:
    mem_schemas, mem_handlers = build_memory_tools(store, vault)
    task_schemas, task_handlers = build_task_tools(store, vault)
    schemas = [
        s
        for s in mem_schemas + task_schemas
        if s["function"]["name"] in CAPTURE_TOOL_NAMES
    ]
    handlers = {
        n: h
        for n, h in {**mem_handlers, **task_handlers}.items()
        if n in CAPTURE_TOOL_NAMES
    }
    return schemas, handlers


def transcript_block(messages: list[tuple[str, str]]) -> str:
    if not messages:
        return "(sin mensajes de chat ese día)"
    lines = []
    for role, content in messages:
        label = "Jon" if role == "user" else "Jone"
        text = (content or "").strip()
        if not text:
            continue
        lines.append(f"{label}: {text}")
    blob = "\n".join(lines)
    if len(blob) > MAX_TRANSCRIPT_CHARS:
        blob = "…[transcript truncado]\n" + blob[-MAX_TRANSCRIPT_CHARS:]
    return blob


async def _execute_tool(handlers: dict[str, Any], tool_call: Any) -> str:
    name = tool_call.function.name
    handler = handlers.get(name)
    if handler is None:
        return f"Herramienta desconocida: {name}"
    try:
        arguments = json.loads(tool_call.function.arguments or "{}")
    except json.JSONDecodeError:
        return f"No pude interpretar los argumentos para {name}."
    try:
        return await handler(arguments)
    except Exception:
        logger.exception("Review tool %s failed", name)
        return f"La herramienta {name} falló."


async def run_tool_loop(
    client: openai.AsyncOpenAI,
    *,
    system: str,
    user_payload: str,
    tools: list[dict],
    handlers: dict[str, Any],
    max_tokens: int = 2500,
) -> str:
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_payload},
    ]
    final_text: str | None = None

    for _ in range(MAX_TOOL_ITERS):
        response = await client.chat.completions.create(
            model=settings.openrouter_model,
            max_tokens=min(settings.llm_max_tokens, max_tokens),
            messages=messages,
            tools=tools or None,
        )
        message = response.choices[0].message
        tool_calls = message.tool_calls
        if not tool_calls:
            final_text = (message.content or "").strip() or "(vacío)"
            break

        messages.append(
            {
                "role": "assistant",
                "content": message.content,
                "tool_calls": [tc.model_dump() for tc in tool_calls],
            }
        )
        for tool_call in tool_calls:
            result = await _execute_tool(handlers, tool_call)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                }
            )

    if final_text is None:
        final_text = "Me enredé con demasiadas tools. Prueba otra vez."
    return final_text
