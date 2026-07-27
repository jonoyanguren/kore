"""Chat completion loop with tool use, via OpenRouter.

Owns the tool loop: call the model, execute tool calls, feed results back,
until a final text answer or MAX_TOOL_ITERATIONS. System prompt comes from
PromptAssembler; same-day session history is loaded from MemoryStore.

Big asks: gather with tools, then a forced synthesis turn (no tools) so the
user never gets an empty reply after a long tool chain.
"""

from __future__ import annotations

import base64
import json
import logging
import re
from typing import Any, Awaitable, Callable

import openai

from app.config import settings
from app.kernel.prompt_assembler import PromptAssembler
from app.kernel.skill_registry import Skill
from app.storage.memory import MemoryStore

logger = logging.getLogger(__name__)

ToolHandler = Callable[[dict[str, Any]], Awaitable[str]]

MAX_TOOL_ITERATIONS = 8
SESSION_HISTORY_LIMIT = 20
SYNTH_MAX_TOKENS = 4096

# OpenRouter's free-model router — picks among free models, filtering for
# tool-calling support. Used as a one-time fallback when the configured
# (paid) model returns 402 Insufficient Credits.
_STRONG_HINT = re.compile(
    r"(?i)\b("
    r"megaprompt|mega[- ]?prompt|coach|coaching|solo\s*q|soloq|"
    r"investiga|research|auditor[ií]a|plan completo|plan detallado|"
    r"[uú]ltimas?\s*\d+\s*partidas|haz un plan y|modelo fuerte|/strong"
    r")\b"
)


def wants_strong_model(user_text: str) -> bool:
    """Heuristic: long / coaching / research asks → strong model."""
    t = (user_text or "").strip()
    if len(t) >= 400:
        return True
    return bool(_STRONG_HINT.search(t))


def resolve_model(*, strong: bool = False) -> str:
    primary = (settings.openrouter_model or "").strip() or "anthropic/claude-sonnet-4.6"
    heavy = (settings.openrouter_model_strong or "").strip()
    if strong and heavy:
        return heavy
    return primary


FALLBACK_MODEL = "openrouter/free"

_SYNTH_NUDGE = (
    "STOP. No llames más tools. Con los resultados de tools de este turno, "
    "responde YA en español (texto plano):\n"
    "1) Plan corto (3–6 pasos)\n"
    "2) Hallazgos de lo que ya miraste\n"
    "3) Resumen accionable\n"
    "4) Un solo siguiente paso\n"
    "Si faltan datos, dilo y entrega igual un partial útil. "
    "No digas solo que vas a buscar — escribe la respuesta."
)


def _user_content(
    user_text: str,
    *,
    image_bytes: bytes | None = None,
    image_mime: str = "image/jpeg",
) -> str | list[dict[str, Any]]:
    """Build OpenAI-compatible user content (text or multimodal parts)."""
    if not image_bytes:
        return user_text
    b64 = base64.b64encode(image_bytes).decode("ascii")
    data_url = f"data:{image_mime};base64,{b64}"
    return [
        {"type": "text", "text": user_text},
        {"type": "image_url", "image_url": {"url": data_url}},
    ]


def _parse_tool_arguments(raw: str | None) -> dict[str, Any] | None:
    """Parse tool args JSON; tolerate minor truncation from the model."""
    text = (raw or "").strip() or "{}"
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else {"value": data}
    except json.JSONDecodeError:
        repaired = text
        if repaired.count('"') % 2 == 1:
            repaired += '"'
        if not repaired.endswith("}"):
            repaired += "}"
        try:
            data = json.loads(repaired)
            if isinstance(data, dict):
                logger.warning("Repaired truncated tool arguments JSON")
                return data
        except json.JSONDecodeError:
            pass
        logger.warning("Could not parse tool arguments: %s", text[:200])
        return None


def _tool_calls_for_history(tool_calls: list[Any]) -> list[dict[str, Any]]:
    """Serialize tool_calls for the next OpenRouter turn (drop nulls)."""
    out: list[dict[str, Any]] = []
    for tc in tool_calls:
        fn = getattr(tc, "function", None)
        if fn is None:
            continue
        name = getattr(fn, "name", None) or ""
        args = getattr(fn, "arguments", None) or "{}"
        item: dict[str, Any] = {
            "id": getattr(tc, "id", None) or f"call_{len(out)}",
            "type": "function",
            "function": {"name": name, "arguments": args},
        }
        out.append(item)
    return out


def _is_blank_reply(text: str | None) -> bool:
    t = (text or "").strip()
    if not t:
        return True
    return t in ("(respuesta vacía)", "(sin herramientas válidas)")


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
        persist_user_text: str | None = None,
        image_bytes: bytes | None = None,
        image_mime: str = "image/jpeg",
        on_status: Callable[[str], Awaitable[None]] | None = None,
    ) -> str:
        """Return a reply for `user_text` (optional image). Never raises.

        `persist_user_text` — if set, store this in session history instead of
        `user_text` (e.g. strip UI space prefixes from the transcript).
        `on_status` receives short Spanish labels while thinking / using tools
        (for the web console live status line).
        """

        async def status(msg: str) -> None:
            if on_status is None:
                return
            try:
                await on_status(msg)
            except Exception:
                logger.exception("on_status callback failed")

        try:
            system_prompt = await self._prompt_assembler.assemble(
                active_skill=active_skill
            )
        except Exception:
            logger.exception("Failed to assemble system prompt")
            return "No pude montar el contexto — prueba otra vez."

        messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]

        try:
            for role, content in await self._memory.recent_messages(
                SESSION_HISTORY_LIMIT
            ):
                if role in ("user", "assistant") and content.strip():
                    messages.append({"role": role, "content": content})
        except Exception:
            logger.exception("Failed to load session history")

        messages.append(
            {
                "role": "user",
                "content": _user_content(
                    user_text, image_bytes=image_bytes, image_mime=image_mime
                ),
            }
        )

        model = resolve_model(strong=wants_strong_model(user_text))
        used_fallback = False
        final_text: str | None = None
        used_any_tool = False
        if model != resolve_model(strong=False):
            await status("Modelo fuerte…")
            logger.info("Using strong model %s", model)
        await status("Pensando…")
        try:
            for iteration in range(MAX_TOOL_ITERATIONS):
                await status("Consultando modelo…")
                # Last tool-iteration: nudge toward answering instead of more tools
                call_tools = self._tools or None
                if iteration >= MAX_TOOL_ITERATIONS - 1 and used_any_tool:
                    call_tools = None

                response, err = await self._create(
                    model=model,
                    messages=messages,
                    tools=call_tools,
                    max_tokens=settings.llm_max_tokens,
                )
                if err == "rate_limit":
                    return (
                        "Estoy con rate limit ahora mismo — prueba de nuevo en un minuto."
                    )
                if err == "connection":
                    return "No logro conectar con el modelo ahora mismo. Prueba en un rato."
                if err == "upstream":
                    return "El servicio está teniendo problemas — prueba en un rato."
                if err == "api":
                    return "Algo falló hablando con el modelo."
                if err == "unexpected":
                    return "Algo salió mal de forma inesperada. Perdón por eso."
                if err == "no_credits":
                    if not used_fallback:
                        logger.warning(
                            "Out of OpenRouter credits — falling back to %s",
                            FALLBACK_MODEL,
                        )
                        model = FALLBACK_MODEL
                        used_fallback = True
                        continue
                    return "Sin saldo en OpenRouter — recarga y reintenta."
                if response is None:
                    return "Algo falló hablando con el modelo."

                choices = getattr(response, "choices", None) or []
                if not choices or choices[0] is None:
                    logger.warning(
                        "OpenRouter returned empty choices (model=%s)", model
                    )
                    break

                choice = choices[0]
                if choice.finish_reason == "content_filter":
                    return "No puedo ayudarte con eso."

                message = choice.message
                if message is None:
                    logger.warning("OpenRouter choice missing message")
                    break

                tool_calls = message.tool_calls
                if not tool_calls or call_tools is None:
                    text = (message.content or "").strip()
                    if _is_blank_reply(text):
                        # Need synthesis if we gathered tools; else leave blank for synth
                        break
                    if used_fallback:
                        text = (
                            "[Sin saldo en OpenRouter — esta respuesta viene de un "
                            "modelo gratis, peor calidad y puede fallar con "
                            "ClickUp/LoL. Recarga saldo cuando puedas.]\n\n" + text
                        )
                    await status("Redactando…")
                    final_text = text
                    break

                serialized = _tool_calls_for_history(list(tool_calls))
                if not serialized:
                    text = (message.content or "").strip()
                    if not _is_blank_reply(text):
                        final_text = text
                    break

                used_any_tool = True
                messages.append(
                    {
                        "role": "assistant",
                        "content": message.content,
                        "tool_calls": serialized,
                    }
                )
                for tool_call in tool_calls:
                    fn = getattr(tool_call, "function", None)
                    tool_name = (getattr(fn, "name", None) if fn else None) or "tool"
                    await status(f"Usando {tool_name}…")
                    result = await self._execute_tool(tool_call)
                    # Cap huge tool dumps so synthesis still fits
                    if len(result) > 8000:
                        result = result[:8000] + "\n…[tool output truncado]"
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": getattr(tool_call, "id", None)
                            or f"call_{tool_name}",
                            "content": result,
                        }
                    )
        except Exception:
            logger.exception("Unexpected error in tool loop")
            return "Me he tropezado a mitad de la respuesta — prueba otra vez."

        if _is_blank_reply(final_text):
            await status("Resumiendo…")
            synth = await self._synthesize(
                model=model,
                messages=messages,
                used_fallback=used_fallback,
            )
            if synth:
                final_text = synth
            elif final_text is None:
                logger.warning("Hit MAX_TOOL_ITERATIONS / empty without synthesis")
                final_text = (
                    "Me enredé en una tarea gorda. Mejor en dos turns: "
                    "1) «haz solo el plan» 2) «ejecuta el paso 1». "
                    "¿Empezamos por el plan?"
                )

        if persist:
            try:
                history_user = (
                    persist_user_text if persist_user_text is not None else user_text
                )
                if image_bytes is not None:
                    history_user = f"[imagen] {history_user}".strip()
                await self._memory.add_message("user", history_user)
                await self._memory.add_message("assistant", final_text)
            except Exception:
                logger.exception("Failed to persist session messages")

        return final_text or "(sin respuesta)"

    async def _create(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        max_tokens: int,
    ) -> tuple[Any | None, str | None]:
        """Return (response, error_code). error_code None means ok."""
        try:
            kwargs: dict[str, Any] = {
                "model": model,
                "max_tokens": max_tokens,
                "messages": messages,
            }
            if tools:
                kwargs["tools"] = tools
            response = await self._client.chat.completions.create(**kwargs)
            return response, None
        except openai.RateLimitError:
            logger.warning("OpenRouter rate limit hit")
            return None, "rate_limit"
        except openai.APIConnectionError:
            logger.exception("Could not reach OpenRouter")
            return None, "connection"
        except openai.APIStatusError as e:
            if e.status_code == 402:
                return None, "no_credits"
            if e.status_code >= 500:
                logger.warning("OpenRouter upstream error: %s", e)
                return None, "upstream"
            logger.exception("OpenRouter API error: %s", e)
            return None, "api"
        except Exception:
            logger.exception("Unexpected error calling OpenRouter")
            return None, "unexpected"

    async def _synthesize(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        used_fallback: bool,
    ) -> str | None:
        """Force a text-only wrap-up after tools / empty final message."""
        synth_messages = list(messages)
        synth_messages.append({"role": "user", "content": _SYNTH_NUDGE})
        response, err = await self._create(
            model=model,
            messages=synth_messages,
            tools=None,
            max_tokens=max(settings.llm_max_tokens, SYNTH_MAX_TOKENS),
        )
        if err or response is None:
            logger.warning("Synthesis call failed: %s", err)
            return None
        choices = getattr(response, "choices", None) or []
        if not choices or choices[0] is None or choices[0].message is None:
            return None
        text = (choices[0].message.content or "").strip()
        if not text:
            return None
        if used_fallback:
            text = (
                "[Sin saldo en OpenRouter — modelo gratis.]\n\n" + text
            )
        return text

    async def _execute_tool(self, tool_call: Any) -> str:
        fn = getattr(tool_call, "function", None)
        if fn is None:
            return "Llamada a herramienta sin función."
        name = getattr(fn, "name", None) or ""
        if not name:
            return "Herramienta sin nombre."
        handler = self._handlers.get(name)
        if handler is None:
            logger.warning("Model requested unknown tool: %s", name)
            return f"Herramienta desconocida: {name}"

        arguments = _parse_tool_arguments(getattr(fn, "arguments", None))
        if arguments is None:
            return (
                f"No pude interpretar los argumentos para {name} "
                "(JSON truncado). Reintenta con menos detalle."
            )

        try:
            return await handler(arguments)
        except Exception:
            logger.exception("Tool %s failed", name)
            return f"La herramienta {name} falló al ejecutarse."
