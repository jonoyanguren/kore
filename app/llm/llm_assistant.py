"""Chat completion loop with tool use, via OpenRouter.

Owns the tool loop: call the model, execute tool calls, feed results back,
until a final text answer or MAX_TOOL_ITERATIONS. System prompt comes from
PromptAssembler; same-day session history is loaded from MemoryStore.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Awaitable, Callable

import openai

from app.config import settings
from app.kernel.prompt_assembler import PromptAssembler
from app.kernel.skill_registry import Skill
from app.storage.memory import MemoryStore

logger = logging.getLogger(__name__)

ToolHandler = Callable[[dict[str, Any]], Awaitable[str]]

MAX_TOOL_ITERATIONS = 6
SESSION_HISTORY_LIMIT = 20

# OpenRouter's free-model router — picks among free models, filtering for
# tool-calling support. Used as a one-time fallback when the configured
# (paid) model returns 402 Insufficient Credits.
FALLBACK_MODEL = "openrouter/free"


class LLMAssistant:
    """Wraps an OpenAI-compatible client (OpenRouter) with a tool-use loop."""

    def __init__(
        self,
        client: openai.AsyncOpenAI,
        tools: list[dict[str, Any]],
        handlers: dict[str, ToolHandler],
        memory: MemoryStore,
        prompt_assembler: PromptAssembler,
    ) -> None:
        self._client = client
        self._tools = tools
        self._handlers = handlers
        self._memory = memory
        self._prompt_assembler = prompt_assembler

    async def ask(
        self,
        user_text: str,
        *,
        active_skill: Skill | None = None,
        persist: bool = True,
    ) -> str:
        """Return a reply for `user_text`. Never raises — always returns a string."""
        system_prompt = await self._prompt_assembler.assemble(active_skill=active_skill)
        messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]

        for role, content in await self._memory.recent_messages(SESSION_HISTORY_LIMIT):
            if role in ("user", "assistant") and content.strip():
                messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": user_text})

        model = settings.openrouter_model
        used_fallback = False
        final_text: str | None = None

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
                    logger.warning(
                        "Out of OpenRouter credits — falling back to %s", FALLBACK_MODEL
                    )
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
                final_text = text
                break

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

        if final_text is None:
            logger.warning("Hit MAX_TOOL_ITERATIONS without a final answer")
            final_text = (
                "Me enredé encadenando herramientas — prueba a reformular la pregunta."
            )

        if persist:
            try:
                await self._memory.add_message("user", user_text)
                await self._memory.add_message("assistant", final_text)
            except Exception:
                logger.exception("Failed to persist session messages")

        return final_text

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
