"""Chat completion wrapper for the Phase 1 chat flow, via OpenRouter.

OpenRouter exposes an OpenAI-compatible endpoint that proxies many
providers/models behind one API key — the model is fully configurable via
OPENROUTER_MODEL in .env, no code change needed to switch providers.

No conversation history, no tools, no streaming (replies are short chat
messages, not long documents).
"""

from __future__ import annotations

import logging

import openai

from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a helpful personal assistant chatting with your one owner over "
    "Telegram. Keep replies concise and conversational, and reply in the "
    "same language the user writes in. Reply in plain text only — do not "
    "use Markdown formatting (no **bold**, _italics_, backticks, or "
    "headers), since Telegram will show it as literal characters instead "
    "of rendering it."
)


class LLMAssistant:
    """Thin wrapper over an OpenAI-compatible client pointed at OpenRouter."""

    def __init__(self, client: openai.AsyncOpenAI) -> None:
        self._client = client

    async def ask(self, user_text: str) -> str:
        """Return a reply for `user_text`. Never raises — always returns a string."""
        try:
            response = await self._client.chat.completions.create(
                model=settings.openrouter_model,
                max_tokens=settings.llm_max_tokens,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_text},
                ],
            )
        except openai.RateLimitError:
            logger.warning("OpenRouter rate limit hit")
            return "Estoy con rate limit ahora mismo — prueba de nuevo en un minuto."
        except openai.APIConnectionError:
            logger.exception("Could not reach OpenRouter")
            return "No logro conectar con el modelo ahora mismo. Prueba en un rato."
        except openai.APIStatusError as e:
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

        return choice.message.content or "(respuesta vacía)"
