"""FastAPI app: Telegram webhook -> companion kernel -> LLM tools -> reply."""

from __future__ import annotations

import asyncio
import logging
import secrets
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass

import httpx
import openai
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request

from app.config import settings
from app.integrations.clickup.clickup_client import ClickUpClient
from app.integrations.clickup.tools import build_clickup_tools
from app.integrations.lol.opgg_client import call_lol_tool, list_lol_tools
from app.kernel.command_router import CommandRouter
from app.kernel.dream import run_dream
from app.kernel.project_tools import build_project_tools
from app.kernel.prompt_assembler import PromptAssembler
from app.kernel.scheduler import run_scheduled_dream
from app.kernel.skill_registry import SkillRegistry
from app.kernel.time_tools import build_time_tools
from app.llm.llm_assistant import LLMAssistant, ToolHandler
from app.paths import DEV_SKILLS_DIR, PROMPTS_DIR, SKILLS_DIR
from app.storage.memory import MemoryStore
from app.storage.task_tools import build_task_tools
from app.storage.tools import build_memory_tools
from app.storage.vault import Vault
from app.telegram.client import TelegramClient
from app.telegram.schemas import TelegramUpdate
from app.timeutil import format_madrid_clock, session_date_str

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# If Jon sends a photo and then a separate text ("qué es esto?"), attach the
# photo to that text. Wait this long before answering a caption-less photo alone.
PHOTO_FOLLOWUP_WAIT_SECONDS = 3.0
PENDING_PHOTO_TTL_SECONDS = 90.0

PHOTO_DESCRIBE_PROMPT = (
    "El usuario ha enviado esta imagen sin texto. "
    "Di qué es / qué se ve, breve y útil. "
    "Responde solo a la imagen. No te presentes. "
    "No saques temas de memoria no relacionados (ITV, etc.). "
    "No guardes en memoria ni diario. No ofrezcas planes ni 'si quieres…'."
)


@dataclass
class PendingPhoto:
    image_bytes: bytes
    mime: str
    created_at: float
    token: str


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
        default_headers={"X-Title": "kore"},
    )

    memory_store = MemoryStore(settings.storage_db_path)
    await memory_store.init()
    vault = Vault(settings.resolved_vault_root())
    vault.ensure()

    memory_tool_schemas, memory_handlers = build_memory_tools(memory_store, vault)
    task_tool_schemas, task_handlers = build_task_tools(memory_store, vault)
    time_tool_schemas, time_handlers = build_time_tools()
    project_tool_schemas, project_handlers = build_project_tools()

    if settings.load_dev_skills:
        skill_registry = SkillRegistry(SKILLS_DIR, DEV_SKILLS_DIR)
    else:
        skill_registry = SkillRegistry(SKILLS_DIR)
    skill_registry.load()
    prompt_assembler = PromptAssembler(PROMPTS_DIR, skill_registry, memory_store)
    command_router = CommandRouter(skill_registry)

    clickup_client = ClickUpClient(settings.clickup_api_token, http_client)
    clickup_tool_schemas, clickup_handlers = build_clickup_tools(clickup_client)

    try:
        lol_tool_schemas = await list_lol_tools()
    except Exception:
        logger.exception(
            "Could not load LoL tools from OP.GG at startup — continuing without them"
        )
        lol_tool_schemas = []

    lol_handlers: dict[str, ToolHandler] = {
        tool["function"]["name"]: (
            lambda args, _name=tool["function"]["name"]: call_lol_tool(_name, args)
        )
        for tool in lol_tool_schemas
    }

    all_tools = (
        memory_tool_schemas
        + task_tool_schemas
        + time_tool_schemas
        + project_tool_schemas
        + clickup_tool_schemas
        + lol_tool_schemas
    )
    all_handlers: dict[str, ToolHandler] = {
        **memory_handlers,
        **task_handlers,
        **time_handlers,
        **project_handlers,
        **clickup_handlers,
        **lol_handlers,
    }

    telegram = TelegramClient(settings.telegram_bot_token, http_client)
    app.state.telegram = telegram
    app.state.memory = memory_store
    app.state.vault = vault
    app.state.llm_client = llm_client
    app.state.skills = skill_registry
    app.state.commands = command_router
    app.state.pending_photos = {}  # chat_id -> PendingPhoto
    app.state.llm = LLMAssistant(
        llm_client, all_tools, all_handlers, memory_store, prompt_assembler
    )

    yield

    await http_client.aclose()
    await llm_client.close()


app = FastAPI(lifespan=lifespan)


TYPING_REFRESH_SECONDS = 4  # Telegram's "typing..." indicator expires after ~5s


async def _keep_typing(telegram: TelegramClient, chat_id: int) -> None:
    try:
        while True:
            await telegram.send_typing(chat_id)
            await asyncio.sleep(TYPING_REFRESH_SECONDS)
    except asyncio.CancelledError:
        pass


def _claim_pending_photo(
    pending_photos: dict[int, PendingPhoto], chat_id: int
) -> PendingPhoto | None:
    pending = pending_photos.pop(chat_id, None)
    if pending is None:
        return None
    if time.time() - pending.created_at > PENDING_PHOTO_TTL_SECONDS:
        return None
    return pending


async def handle_text_message(
    telegram: TelegramClient,
    llm: LLMAssistant,
    commands: CommandRouter,
    memory: MemoryStore,
    skills: SkillRegistry,
    pending_photos: dict[int, PendingPhoto],
    chat_id: int,
    text: str,
    *,
    vault: Vault | None = None,
    llm_client: openai.AsyncOpenAI | None = None,
) -> None:
    match = commands.match(text)

    if match is not None and match.builtin == "start":
        await handle_start(telegram, chat_id)
        return

    if match is not None and match.builtin == "skills":
        catalog = skills.catalog_text()
        await telegram.send_message(
            chat_id,
            f"Skills disponibles:\n{catalog}\n\n"
            f"También: /hora /diario /tareas /agenda /dream /captura",
        )
        return

    if match is not None and match.builtin == "diario":
        day = session_date_str()
        entries = await memory.list_diary_for_day(day)
        if not entries:
            await telegram.send_message(chat_id, f"Diario vacío para {day}.")
        else:
            lines = [f"- {entry}" for _id, entry in entries]
            await telegram.send_message(chat_id, f"Diario {day}:\n" + "\n".join(lines))
        return

    # Fast path for /hora — authoritative clock, no LLM
    if match is not None and match.skill and match.skill.name == "time-madrid":
        await telegram.send_message(chat_id, format_madrid_clock())
        return

    # /dream — consolidate (default yesterday; optional YYYY-MM-DD arg)
    if match is not None and match.skill and match.skill.name == "dream":
        if vault is None or llm_client is None:
            await telegram.send_message(chat_id, "Sueño no disponible ahora.")
            return
        # Manual: today (or YYYY-MM-DD arg). Cron uses yesterday explicitly.
        day_arg = match.args.strip() or session_date_str()
        typing_task = asyncio.create_task(_keep_typing(telegram, chat_id))
        try:
            summary = await run_dream(
                memory,
                vault,
                llm_client,
                day=day_arg,
                telegram=None,
                notify=False,
            )
            text_out = summary if len(summary) < 3500 else summary[:3490] + "…"
            await telegram.send_message(chat_id, text_out)
        except Exception:
            logger.exception("Dream command failed")
            await telegram.send_message(chat_id, "El sueño falló. Prueba otra vez.")
        finally:
            typing_task.cancel()
        return

    # /tareas /agenda without args — list from SQLite
    if match is not None and match.skill and match.skill.name == "tasks" and not match.args:
        if match.command == "/agenda":
            rows = await memory.list_agenda_upcoming(limit=20)
            if not rows:
                await telegram.send_message(chat_id, "Agenda vacía.")
            else:
                lines = [f"- {starts} — {title}" for _i, starts, title, _st in rows]
                await telegram.send_message(chat_id, "Agenda:\n" + "\n".join(lines))
            return
        rows = await memory.list_tasks(status="open", limit=30)
        from app.storage.memory import format_tasks_message

        await telegram.send_message(
            chat_id, format_tasks_message(rows, heading="Tareas abiertas")
        )
        return

    user_text = text
    active_skill = None
    if match is not None and match.skill is not None:
        active_skill = match.skill
        if match.args:
            user_text = match.args
        else:
            user_text = (
                f"Ejecuta la skill {match.skill.name} "
                f"(comando {match.command})."
            )

    claimed = _claim_pending_photo(pending_photos, chat_id)
    image_bytes = claimed.image_bytes if claimed else None
    image_mime = claimed.mime if claimed else "image/jpeg"

    typing_task = asyncio.create_task(_keep_typing(telegram, chat_id))
    try:
        reply = await llm.ask(
            user_text,
            active_skill=active_skill,
            image_bytes=image_bytes,
            image_mime=image_mime,
        )
        await telegram.send_message(chat_id, reply)
    except Exception:
        logger.exception("Unhandled error processing message for chat_id=%s", chat_id)
        await telegram.send_message(chat_id, "Algo salió mal procesando tu mensaje.")
    finally:
        typing_task.cancel()


async def handle_start(telegram: TelegramClient, chat_id: int) -> None:
    name = settings.assistant_name
    await telegram.send_message(
        chat_id,
        f"¡Hola! Soy {name}. Ya estoy en línea — escríbeme lo que necesites. "
        f"Comandos: /skills /hora /diario /tareas /agenda /dream",
    )


async def handle_photo_message(
    telegram: TelegramClient,
    llm: LLMAssistant,
    pending_photos: dict[int, PendingPhoto],
    chat_id: int,
    file_id: str,
    caption: str | None,
) -> None:
    typing_task = asyncio.create_task(_keep_typing(telegram, chat_id))
    try:
        image_bytes, mime = await telegram.download_file(file_id)
        caption_text = (caption or "").strip()

        if caption_text:
            reply = await llm.ask(
                caption_text, image_bytes=image_bytes, image_mime=mime
            )
            await telegram.send_message(chat_id, reply)
            return

        # No caption: wait briefly so a follow-up "qué es esto?" can claim the photo.
        token = uuid.uuid4().hex
        pending_photos[chat_id] = PendingPhoto(
            image_bytes=image_bytes,
            mime=mime,
            created_at=time.time(),
            token=token,
        )
        await asyncio.sleep(PHOTO_FOLLOWUP_WAIT_SECONDS)
        pending = pending_photos.get(chat_id)
        if pending is None or pending.token != token:
            # Follow-up text claimed this photo — do not answer twice.
            return

        pending_photos.pop(chat_id, None)
        reply = await llm.ask(
            PHOTO_DESCRIBE_PROMPT, image_bytes=image_bytes, image_mime=mime
        )
        await telegram.send_message(chat_id, reply)
    except Exception:
        logger.exception("Unhandled error processing photo for chat_id=%s", chat_id)
        await telegram.send_message(
            chat_id, "No pude leer esa imagen. Prueba otra vez o mándala más pequeña."
        )
    finally:
        typing_task.cancel()


async def handle_non_text(telegram: TelegramClient, chat_id: int) -> None:
    await telegram.send_message(
        chat_id,
        "Por ahora entiendo texto e imágenes. Ese tipo de mensaje aún no.",
    )


@app.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok"}


@app.post("/internal/cron/dream")
async def cron_dream(request: Request) -> dict:
    """External cron (GitHub Actions ~03:00 Madrid). No in-process polling."""
    auth = request.headers.get("authorization", "")
    expected = f"Bearer {settings.cron_secret}" if settings.cron_secret else ""
    if not expected or not secrets.compare_digest(auth, expected):
        raise HTTPException(status_code=403, detail="forbidden")

    result = await run_scheduled_dream(
        request.app.state.memory,
        request.app.state.vault,
        request.app.state.llm_client,
        request.app.state.telegram,
    )
    return {"ok": True, **result}


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
        return {"ok": True}

    chat_id = update.message.chat.id
    if chat_id != settings.telegram_allowed_chat_id:
        logger.warning("Ignoring message from non-whitelisted chat_id=%s", chat_id)
        return {"ok": True}

    telegram: TelegramClient = request.app.state.telegram
    llm: LLMAssistant = request.app.state.llm
    commands: CommandRouter = request.app.state.commands
    memory: MemoryStore = request.app.state.memory
    skills: SkillRegistry = request.app.state.skills
    pending_photos: dict[int, PendingPhoto] = request.app.state.pending_photos
    vault: Vault = request.app.state.vault
    llm_client: openai.AsyncOpenAI = request.app.state.llm_client
    message = update.message
    text = message.text

    if message.photo:
        # Telegram sends several sizes; last is the largest.
        largest = message.photo[-1]
        background_tasks.add_task(
            handle_photo_message,
            telegram,
            llm,
            pending_photos,
            chat_id,
            largest.file_id,
            message.caption,
        )
    elif text is None:
        background_tasks.add_task(handle_non_text, telegram, chat_id)
    else:
        background_tasks.add_task(
            handle_text_message,
            telegram,
            llm,
            commands,
            memory,
            skills,
            pending_photos,
            chat_id,
            text,
            vault=vault,
            llm_client=llm_client,
        )

    return {"ok": True}
