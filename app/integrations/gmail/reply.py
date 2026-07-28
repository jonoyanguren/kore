"""Gmail reply: read mail → LLM draft → send (D17)."""

from __future__ import annotations

import logging
import re
from email.utils import parseaddr
from typing import Any

import openai

from app.integrations.gmail.client import GmailClient, GmailMessageDetail
from app.llm.llm_assistant import resolve_model

logger = logging.getLogger(__name__)

PROPOSE_REPLY_SYSTEM = """Eres Jone, assistant de Jon. Redactas UNA respuesta por email.

Responde SOLO el cuerpo del mail (texto plano), sin asunto, sin JSON, sin markdown fences.

Reglas:
- Español (salvo que el mail original esté claramente en otro idioma).
- Tono: profesional-cercano, como Jon; corto y concreto.
- No inventes compromisos, fechas ni datos que no estén en el mail.
- Si falta info para responder bien, pide lo mínimo en 1–2 frases.
- Sin firma larga; como mucho "Jon" al final si encaja.
- No digas que eres una IA."""


def reply_subject(subject: str) -> str:
    s = (subject or "").strip() or "(sin asunto)"
    if re.match(r"^(re|fw|fwd)\s*:", s, flags=re.I):
        return s
    return f"Re: {s}"


def reply_to_address(msg: GmailMessageDetail) -> str:
    raw = (msg.reply_to or msg.from_ or "").strip()
    _name, addr = parseaddr(raw)
    return addr or raw


def _fallback_body(msg: GmailMessageDetail) -> str:
    who = parseaddr(msg.from_)[0] or msg.from_.split("<")[0].strip() or "hola"
    first = who.split()[0] if who else "hola"
    return (
        f"Hola {first},\n\n"
        f"Gracias por el mail — lo miro y te contesto con detalle.\n\n"
        f"Jon"
    )


async def propose_reply_draft(
    llm: openai.AsyncOpenAI,
    msg: GmailMessageDetail,
) -> str:
    body = (msg.body_text or msg.snippet or "").strip()
    if len(body) > 6000:
        body = body[:6000] + "\n…"
    user = (
        f"De: {msg.from_}\n"
        f"Para (Reply-To/From): {reply_to_address(msg)}\n"
        f"Asunto: {msg.subject}\n"
        f"Fecha: {msg.date}\n\n"
        f"--- Cuerpo ---\n{body or '(sin cuerpo; solo snippet)'}"
    )
    try:
        response = await llm.chat.completions.create(
            model=resolve_model(strong=True),
            messages=[
                {"role": "system", "content": PROPOSE_REPLY_SYSTEM},
                {"role": "user", "content": user},
            ],
            max_tokens=800,
            temperature=0.4,
        )
        content = (response.choices[0].message.content or "").strip()
        if content.startswith("```"):
            content = re.sub(r"^```(?:\w+)?\s*", "", content)
            content = re.sub(r"\s*```$", "", content)
        if content:
            return content
    except Exception:
        logger.exception("propose_reply_draft LLM failed; using fallback")
    return _fallback_body(msg)


async def draft_reply(
    *,
    gmail: GmailClient,
    llm: openai.AsyncOpenAI,
    message_id: str,
) -> dict[str, Any]:
    msg = await gmail.get_message_detail(message_id)
    if msg is None:
        raise LookupError("message_not_found")
    body = await propose_reply_draft(llm, msg)
    return {
        "message_id": msg.id,
        "thread_id": msg.thread_id,
        "to": reply_to_address(msg),
        "subject": reply_subject(msg.subject),
        "body": body,
        "from": msg.from_,
        "permalink": msg.permalink,
    }


async def send_reply(
    *,
    gmail: GmailClient,
    message_id: str,
    body: str,
) -> dict[str, Any]:
    text = (body or "").strip()
    if not text:
        raise ValueError("empty_body")
    msg = await gmail.get_message_detail(message_id)
    if msg is None:
        raise LookupError("message_not_found")
    to = reply_to_address(msg)
    if not to:
        raise ValueError("no_reply_address")
    sent_id = await gmail.send_reply(
        to=to,
        subject=reply_subject(msg.subject),
        body=text,
        thread_id=msg.thread_id,
        in_reply_to=msg.message_id_header,
        references=msg.references or msg.message_id_header,
    )
    try:
        await gmail.mark_read(message_id, reason="reply")
    except Exception:
        logger.exception("Sent reply but failed to mark original read id=%s", message_id)
    return {
        "ok": True,
        "sent_id": sent_id,
        "to": to,
        "subject": reply_subject(msg.subject),
        "marked_read": True,
    }
