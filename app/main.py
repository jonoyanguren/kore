"""FastAPI app: Telegram webhook -> LLM (via OpenRouter) -> Telegram reply.

Phase 1 — stateless. No conversation history, no commands beyond /start,
no tools. See app/integrations/ and app/storage/ for where later phases
will land.
"""

from __future__ import annotations

import logging
import secrets
from contextlib import asynccontextmanager

import httpx
import openai
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request

from app.config import settings
from app.llm.llm_assistant import LLMAssistant
from app.telegram.client import TelegramClient
from app.telegram.schemas import TelegramUpdate

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Random path segment baked in at import time — defense-in-depth against
# scanners hitting predictable paths. The real security boundary is the
# X-Telegram-Bot-Api-Secret-Token header check below, not this path.
WEBHOOK_PATH = f"/telegram/webhook/{settings.telegram_webhook_path_secret}"


@asynccontextmanager
async def lifespan(app: FastAPI):
    http_client = httpx.AsyncClient(timeout=30.0)
    llm_client = openai.AsyncOpenAI(
        api_key=settings.openrouter_api_key,
        base_url=OPENROUTER_BASE_URL,
        # Recommended by OpenRouter to identify the app in their dashboard —
        # not required, no secret involved.
        default_headers={"X-Title": "jornvis"},
    )

    app.state.telegram = TelegramClient(settings.telegram_bot_token, http_client)
    app.state.llm = LLMAssistant(llm_client)

    yield

    await http_client.aclose()
    await llm_client.close()


app = FastAPI(lifespan=lifespan)


# --- Background handlers -----------------------------------------------
# These run *after* the webhook has already returned 200 to Telegram, so a
# slow Claude call never risks Telegram retrying (and duplicating) delivery.


async def handle_text_message(
    telegram: TelegramClient, llm: LLMAssistant, chat_id: int, text: str
) -> None:
    try:
        await telegram.send_typing(chat_id)
        reply = await llm.ask(text)
        await telegram.send_message(chat_id, reply)
    except Exception:
        # LLMAssistant.ask() and TelegramClient never raise on their own
        # expected failure modes — this is a last-resort safety net so a
        # truly unexpected error still gets a reply instead of silence.
        logger.exception("Unhandled error processing message for chat_id=%s", chat_id)
        await telegram.send_message(chat_id, "Algo salió mal procesando tu mensaje.")


async def handle_start(telegram: TelegramClient, chat_id: int) -> None:
    await telegram.send_message(chat_id, "¡Hola! Ya estoy en línea. Escríbeme lo que necesites.")


async def handle_non_text(telegram: TelegramClient, chat_id: int) -> None:
    await telegram.send_message(chat_id, "Por ahora solo puedo leer mensajes de texto.")


# --- Routes ---------------------------------------------------------------


@app.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok"}


@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks) -> dict:
    token = request.headers.get("x-telegram-bot-api-secret-token", "")
    if not secrets.compare_digest(token, settings.telegram_webhook_secret):
        raise HTTPException(status_code=403, detail="forbidden")

    try:
        body = await request.json()
        update = TelegramUpdate.model_validate(body)
    except Exception:
        logger.warning("Failed to parse Telegram update body")
        raise HTTPException(status_code=400, detail="bad request")

    if update.message is None:
        # edited_message, channel_post, callback_query, etc. — nothing to
        # do with these in Phase 1.
        return {"ok": True}

    chat_id = update.message.chat.id
    if chat_id != settings.telegram_allowed_chat_id:
        logger.warning("Ignoring message from non-whitelisted chat_id=%s", chat_id)
        return {"ok": True}

    telegram: TelegramClient = request.app.state.telegram
    llm: LLMAssistant = request.app.state.llm
    text = update.message.text

    if text is None:
        background_tasks.add_task(handle_non_text, telegram, chat_id)
    elif text.strip() == "/start":
        background_tasks.add_task(handle_start, telegram, chat_id)
    else:
        background_tasks.add_task(handle_text_message, telegram, llm, chat_id, text)

    return {"ok": True}
