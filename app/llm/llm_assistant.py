"""Chat completion loop with tool use, via OpenRouter.

Claude decides which tools to call (LoL stats, ClickUp tasks, notes, ...)
based on the conversation. This module owns the loop: call the model,
execute any requested tool calls, feed results back, repeat until the
model produces a final text answer or MAX_TOOL_ITERATIONS is hit.

Still no conversation history across messages — that's separate, bigger
future work. Durable notes (app/storage/memory.py) are the one thing that
persists: they're re-read and folded into the system prompt on every turn.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Awaitable, Callable

import openai

from app.config import settings
from app.storage.memory import MemoryStore

logger = logging.getLogger(__name__)

ToolHandler = Callable[[dict[str, Any]], Awaitable[str]]

MAX_TOOL_ITERATIONS = 6

# OpenRouter's free-model router — picks among free models, filtering for
# tool-calling support. Used as a one-time fallback when the configured
# (paid) model returns 402 Insufficient Credits, so the bot degrades to
# "works, but might be dumber and worse at tools" instead of going silent.
FALLBACK_MODEL = "openrouter/free"

def _base_system_prompt(assistant_name: str) -> str:
    return (
        f"You are {assistant_name}, a helpful personal companion chatting with "
        "your one owner over Telegram. Your project/system name is Kore; "
        f"when referring to yourself in conversation, use {assistant_name}. "
        "Keep replies concise and conversational, and reply in the same "
        "language the user writes in. Reply in plain text only — do not use "
        "Markdown formatting (no **bold**, _italics_, backticks, or headers), "
        "since Telegram will show it as literal characters instead of "
        "rendering it. You have tools for League of Legends stats, ClickUp "
        "task management, and saving/removing durable notes about the user — "
        "use them whenever the request needs real data instead of guessing, "
        "and save a note whenever the user tells you something worth "
        "remembering for future conversations."
    )


class LLMAssistant:
    """Wraps an OpenAI-compatible client (OpenRouter) with a tool-use loop."""

    def __init__(
        self,
        client: openai.AsyncOpenAI,
        tools: list[dict[str, Any]],
        handlers: dict[str, ToolHandler],
        memory: MemoryStore,
    ) -> None:
        self._client = client
        self._tools = tools
        self._handlers = handlers
        self._memory = memory

    async def _build_system_prompt(self) -> str:
        base = _base_system_prompt(settings.assistant_name)
        notes = await self._memory.list_notes()
        if not notes:
            return base
        notes_block = "\n".join(f"- (id {note_id}) {text}" for note_id, text in notes)
        return f"{base}\n\nThings you already know about the user:\n{notes_block}"

    async def ask(self, user_text: str) -> str:
        """Return a reply for `user_text`. Never raises — always returns a string."""
        system_prompt = await self._build_system_prompt()
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ]
        model = settings.openrouter_model
        used_fallback = False

        for _ in range(MAX_TOOL_ITERATIONS):
            try:
                response = await self._client.chat.completions.create(
                    model=model,
                    max_tokens=settings.llm_max_tokens,
                    messages=messages,
                    tools=self._tools or None,
                )
            except openai.RateLimitError:
                logger.warning("OpenRouter rate limit hit")
                return "Estoy con rate limit ahora mismo — prueba de nuevo en un minuto."
            except openai.APIConnectionError:
                logger.exception("Could not reach OpenRouter")
                return "No logro conectar con el modelo ahora mismo. Prueba en un rato."
            except openai.APIStatusError as e:
                if e.status_code == 402 and not used_fallback:
                    logger.warning("Out of OpenRouter credits — falling back to %s", FALLBACK_MODEL)
                    model = FALLBACK_MODEL
                    used_fallback = True
                    continue
                if e.status_code >= 500:
                    logger.warning("OpenRouter upstream error: %s", e)
                    return "El servicio está teniendo problemas — prueba en un rato."
                logger.exception("OpenRouter API error: %s", e)
                return "Algo falló hablando con el modelo."
            except Exception:
                logger.exception("Unexpected error calling OpenRouter")
                return "Algo salió mal de forma inesperada. Perdón por eso."

            choice = response.choices[0]

            if choice.finish_reason == "content_filter":
                return "No puedo ayudarte con eso."

            message = choice.message
            tool_calls = message.tool_calls

            if not tool_calls:
                text = message.content or "(respuesta vacía)"
                if used_fallback:
                    text = (
                        "[Sin saldo en OpenRouter — esta respuesta viene de un "
                        "modelo gratis, peor calidad y puede fallar con "
                        "ClickUp/LoL. Recarga saldo cuando puedas.]\n\n" + text
                    )
                return text

            # Echo the assistant's tool-call turn back, then append one
            # tool result per call — the API rejects a follow-up request if
            # any tool_call lacks a matching result.
            messages.append(
                {
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": [tc.model_dump() for tc in tool_calls],
                }
            )
            for tool_call in tool_calls:
                result = await self._execute_tool(tool_call)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    }
                )

        logger.warning("Hit MAX_TOOL_ITERATIONS without a final answer")
        return "Me enredé encadenando herramientas — prueba a reformular la pregunta."

    async def _execute_tool(self, tool_call: Any) -> str:
        name = tool_call.function.name
        handler = self._handlers.get(name)
        if handler is None:
            logger.warning("Model requested unknown tool: %s", name)
            return f"Herramienta desconocida: {name}"

        try:
            arguments = json.loads(tool_call.function.arguments or "{}")
        except json.JSONDecodeError:
            logger.exception("Could not parse arguments for tool %s", name)
            return f"No pude interpretar los argumentos para {name}."

        try:
            return await handler(arguments)
        except Exception:
            logger.exception("Tool %s failed", name)
            return f"La herramienta {name} falló al ejecutarse."
