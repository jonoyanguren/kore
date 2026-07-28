"""Turn a Gmail message into a local Kore task (LLM title + project)."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import openai

from app.integrations.gmail.client import GmailClient, GmailMessage
from app.llm.llm_assistant import resolve_model
from app.storage.memory import MemoryStore
from app.storage.task_tools import find_task_collision, sync_tasks_vault
from app.storage.vault import Vault

logger = logging.getLogger(__name__)

PROPOSE_SYSTEM = """Eres Jone. A partir de un email, propones UNA tarea corta para Jon.

Responde SOLO un JSON (sin markdown):
{"title":"...","project":"personal|kore|kimay|lol|... o null","notes":"una línea opcional"}

Reglas:
- title: acción clara, < 80 chars, español, sin "Re:" ni ruido de newsletter.
- project: slug corto si se deduce; si no, null.
- notes: contexto mínimo (quién / qué); no copies el email entero.
- No inventes datos que no estén en el mail."""


def _fallback_proposal(msg: GmailMessage) -> dict[str, Any]:
    title = (msg.subject or "Seguir email").strip()
    title = re.sub(r"^(re|fw|fwd)\s*:\s*", "", title, flags=re.I).strip() or "Seguir email"
    if len(title) > 80:
        title = title[:77] + "…"
    who = (msg.from_ or "").split("<")[0].strip() or msg.from_
    notes = f"De: {who}".strip()
    if msg.snippet:
        notes = f"{notes}. {msg.snippet[:160]}".strip()
    return {"title": title, "project": None, "notes": notes}


async def propose_task_from_email(
    llm: openai.AsyncOpenAI,
    msg: GmailMessage,
) -> dict[str, Any]:
    user = (
        f"De: {msg.from_}\n"
        f"Asunto: {msg.subject}\n"
        f"Fecha: {msg.date}\n"
        f"Snippet: {msg.snippet}\n"
        f"Link: {msg.permalink}"
    )
    try:
        response = await llm.chat.completions.create(
            model=resolve_model(strong=True),
            messages=[
                {"role": "system", "content": PROPOSE_SYSTEM},
                {"role": "user", "content": user},
            ],
            max_tokens=300,
            temperature=0.2,
        )
        content = (response.choices[0].message.content or "").strip()
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\s*", "", content)
            content = re.sub(r"\s*```$", "", content)
        data = json.loads(content)
        title = str(data.get("title") or "").strip()
        if not title:
            return _fallback_proposal(msg)
        project = data.get("project")
        project = (str(project).strip().lower() if project else None) or None
        notes = str(data.get("notes") or "").strip() or None
        return {"title": title[:120], "project": project, "notes": notes}
    except Exception:
        logger.exception("propose_task_from_email LLM failed; using fallback")
        return _fallback_proposal(msg)


async def create_task_from_email(
    *,
    gmail: GmailClient,
    llm: openai.AsyncOpenAI,
    memory: MemoryStore,
    vault: Vault,
    message_id: str,
) -> dict[str, Any]:
    msg = await gmail.get_message(message_id)
    if msg is None:
        return {"ok": False, "error": "message_not_found"}

    proposal = await propose_task_from_email(llm, msg)
    title = proposal["title"]
    collision = await find_task_collision(memory, vault, title)
    if collision:
        # Soft uniqueness: append short from-hint
        who = (msg.from_ or "").split("<")[0].strip()
        if who and who.lower() not in title.lower():
            title = f"{title} ({who})"[:120]
            collision = await find_task_collision(memory, vault, title)
        if collision:
            return {"ok": False, "error": "duplicate", "detail": collision}

    notes = proposal.get("notes") or ""
    if msg.snippet and msg.snippet not in (notes or ""):
        extra = msg.snippet[:200]
        notes = f"{notes}\n{extra}".strip() if notes else extra

    task_id = await memory.add_task(
        title=title,
        notes=notes or None,
        url=msg.permalink,
        project=proposal.get("project"),
        status="open",
    )
    await sync_tasks_vault(memory, vault)
    task = await memory.get_task(task_id)
    assert task is not None
    try:
        await gmail.mark_read(message_id, reason="task")
    except Exception:
        logger.exception("Created task but failed to mark email read id=%s", message_id)
    return {
        "ok": True,
        "task": {
            "id": task.id,
            "title": task.title,
            "status": task.status,
            "project": task.project,
            "url": task.url,
            "notes": task.notes,
            "due_at": task.due_at,
            "priority": task.priority,
        },
        "email": {
            "id": msg.id,
            "subject": msg.subject,
            "from": msg.from_,
        },
        "marked_read": True,
    }
