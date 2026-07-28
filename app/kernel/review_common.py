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
SYNTH_MAX_TOKENS = 4096

# Placeholder the old loop wrote when the model returned blank content.
EMPTY_REPORT_MARKERS = frozenset({"(vacío)", "(sin respuesta)", "(respuesta vacía)"})

_DREAM_SYNTH_NUDGE = (
    "STOP. No llames más tools. Con el contexto de este turno, escribe YA el "
    "mensaje final en español, texto plano, con las secciones obligatorias:\n"
    "Resumen\nTareas importantes\nReuniones\nAyuda\nCierre\n"
    "No respondas vacío ni digas solo '(vacío)'."
)

CAPTURE_TOOL_NAMES = {
    "save_memory",
    "add_diary_entry",
    "add_task",
    "complete_task",
    "delete_task",
    "list_tasks",
    "get_task",
    "update_task",
    "add_agenda_item",
    "list_agenda",
    "forget_memory",
}


def is_blank_report(text: str | None) -> bool:
    """True when the model produced nothing usable for a dream/briefing."""
    t = (text or "").strip()
    if not t:
        return True
    return t.lower() in EMPTY_REPORT_MARKERS


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


def _looks_like_briefing(text: str) -> bool:
    low = text.lower()
    return any(
        h in low
        for h in ("resumen", "tareas importantes", "ayuda", "reuniones", "cierre", "prep")
    )


def _message_text(message: Any) -> str:
    """Prefer visible content; some thinking models leave content blank."""
    content = (getattr(message, "content", None) or "").strip()
    if content:
        return content
    # OpenRouter / DeepSeek V4 may park text in reasoning fields.
    candidates: list[tuple[str, str]] = []
    for attr in ("reasoning", "reasoning_content"):
        raw = getattr(message, attr, None)
        if isinstance(raw, str) and raw.strip():
            candidates.append((attr, raw.strip()))
    extra = getattr(message, "model_extra", None) or {}
    if isinstance(extra, dict):
        for key in ("reasoning", "reasoning_content"):
            raw = extra.get(key)
            if isinstance(raw, str) and raw.strip():
                candidates.append((f"model_extra.{key}", raw.strip()))
    for label, raw in candidates:
        if _looks_like_briefing(raw):
            logger.warning(
                "Model returned blank content; using %s as briefing (%d chars)",
                label,
                len(raw),
            )
            return raw
        logger.warning(
            "Model blank content; %s present (%d chars) but not briefing-shaped",
            label,
            len(raw),
        )
    return ""


async def _synthesize_report(
    client: openai.AsyncOpenAI,
    messages: list[dict[str, Any]],
    *,
    model: str,
    max_tokens: int,
) -> str | None:
    """Forced text-only wrap-up when the model returns blank / only tools."""
    synth_messages = list(messages)
    synth_messages.append({"role": "user", "content": _DREAM_SYNTH_NUDGE})
    response = await client.chat.completions.create(
        model=model,
        max_tokens=min(max(settings.llm_max_tokens, SYNTH_MAX_TOKENS), max_tokens * 2),
        messages=synth_messages,
        tools=None,
    )
    choices = getattr(response, "choices", None) or []
    if not choices or choices[0] is None or choices[0].message is None:
        return None
    text = _message_text(choices[0].message)
    if is_blank_report(text):
        return None
    return text


async def run_tool_loop(
    client: openai.AsyncOpenAI,
    *,
    system: str,
    user_payload: str,
    tools: list[dict],
    handlers: dict[str, Any],
    max_tokens: int = 2500,
    model: str | None = None,
) -> str:
    model_id = (model or settings.openrouter_model).strip()
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_payload},
    ]
    final_text: str | None = None
    used_any_tool = False

    for iteration in range(MAX_TOOL_ITERS):
        # Last iter: force text (no tools) so we don't end on a bare tool chain.
        call_tools = tools or None
        if iteration >= MAX_TOOL_ITERS - 1 and used_any_tool:
            call_tools = None

        response = await client.chat.completions.create(
            model=model_id,
            max_tokens=min(settings.llm_max_tokens, max_tokens),
            messages=messages,
            tools=call_tools,
        )
        choice = response.choices[0]
        message = choice.message
        finish = getattr(choice, "finish_reason", None)
        tool_calls = message.tool_calls if call_tools else None
        if not tool_calls:
            text = _message_text(message)
            if not is_blank_report(text):
                final_text = text
            else:
                logger.warning(
                    "Review loop blank text model=%s finish=%s iter=%d "
                    "content_len=%d",
                    model_id,
                    finish,
                    iteration,
                    len(message.content or ""),
                )
            break

        used_any_tool = True
        # Preserve reasoning fields for DeepSeek V4 thinking + tools round-trip.
        assistant_msg: dict[str, Any] = {
            "role": "assistant",
            "content": message.content,
            "tool_calls": [tc.model_dump() for tc in tool_calls],
        }
        for attr in ("reasoning", "reasoning_content"):
            raw = getattr(message, attr, None)
            if raw is None:
                extra = getattr(message, "model_extra", None) or {}
                if isinstance(extra, dict):
                    raw = extra.get(attr)
            if isinstance(raw, str) and raw:
                assistant_msg[attr] = raw
        messages.append(assistant_msg)
        for tool_call in tool_calls:
            result = await _execute_tool(handlers, tool_call)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                }
            )

    if is_blank_report(final_text):
        logger.warning(
            "Review tool loop blank — forcing synthesis pass model=%s", model_id
        )
        try:
            synth = await _synthesize_report(
                client, messages, model=model_id, max_tokens=max_tokens
            )
        except Exception:
            logger.exception("Review synthesis pass failed")
            synth = None
        if synth:
            final_text = synth
        elif final_text is None and used_any_tool:
            final_text = "Me enredé con demasiadas tools. Prueba otra vez."
        else:
            final_text = ""

    return final_text or ""
