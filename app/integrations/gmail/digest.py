"""LLM digest of Gmail unread — cached beside the DB on /data."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import openai

from app.integrations.gmail.client import GmailClient, GmailMessage
from app.llm.llm_assistant import resolve_model

logger = logging.getLogger(__name__)

DIGEST_TTL_SECONDS = 30 * 60
DIGEST_MAX_MESSAGES = 12
DIGEST_MAX_TOKENS = 700

DIGEST_SYSTEM = """Eres Jone, companion de Jon. Resume su bandeja de entrada.

Reglas:
- Español, texto plano, sin markdown.
- Solo lo importante / accionable. Ignora newsletters, promos, ruido.
- 3–6 bullets cortos. Si no hay nada relevante: una sola línea "Nada urgente en el correo."
- Cada bullet: quién / qué / por qué importa (o qué hacer).
- No inventes mails. No digas que eres un modelo."""


@dataclass
class InboxDigest:
    bullets: list[str]
    message_ids: list[str]
    created_at: float
    email: str = ""

    def fresh(self, *, ttl: float = DIGEST_TTL_SECONDS) -> bool:
        return time.time() - self.created_at < ttl


def digest_path_for_db(storage_db_path: str) -> Path:
    return Path(storage_db_path).resolve().parent / "gmail_digest.json"


def _ids_fingerprint(ids: list[str]) -> str:
    blob = ",".join(sorted(ids))
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def load_digest(path: Path) -> InboxDigest | None:
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    try:
        return InboxDigest(
            bullets=[str(x) for x in (raw.get("bullets") or []) if str(x).strip()],
            message_ids=[str(x) for x in (raw.get("message_ids") or [])],
            created_at=float(raw.get("created_at") or 0),
            email=str(raw.get("email") or ""),
        )
    except (TypeError, ValueError):
        return None


def save_digest(path: Path, digest: InboxDigest) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(asdict(digest), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)
    try:
        path.chmod(0o600)
    except OSError:
        pass


def cached_digest_for(
    path: Path,
    message_ids: list[str],
    *,
    ttl: float = DIGEST_TTL_SECONDS,
) -> InboxDigest | None:
    digest = load_digest(path)
    if digest is None or not digest.fresh(ttl=ttl):
        return None
    if _ids_fingerprint(digest.message_ids) != _ids_fingerprint(message_ids):
        return None
    return digest


def _parse_bullets(text: str) -> list[str]:
    lines: list[str] = []
    for line in (text or "").splitlines():
        s = line.strip()
        if not s:
            continue
        s = re.sub(r"^[-*•]\s+", "", s)
        s = re.sub(r"^\d+[.)]\s+", "", s)
        s = s.strip()
        if s:
            lines.append(s)
    if not lines and (text or "").strip():
        lines = [(text or "").strip()]
    return lines[:8]


def _messages_payload(messages: list[GmailMessage]) -> str:
    blocks: list[str] = []
    for i, m in enumerate(messages[:DIGEST_MAX_MESSAGES], start=1):
        blocks.append(
            f"{i}. id={m.id}\n"
            f"   de: {m.from_}\n"
            f"   asunto: {m.subject}\n"
            f"   fecha: {m.date}\n"
            f"   snippet: {m.snippet}"
        )
    return "\n".join(blocks) if blocks else "(sin mensajes)"


async def generate_inbox_digest(
    llm: openai.AsyncOpenAI,
    messages: list[GmailMessage],
    *,
    email: str = "",
) -> InboxDigest:
    if not messages:
        return InboxDigest(
            bullets=["Nada urgente en el correo."],
            message_ids=[],
            created_at=time.time(),
            email=email,
        )

    model = resolve_model(strong=True)
    user = (
        f"Cuenta: {email or 'Gmail'}\n"
        f"Unread a considerar ({len(messages)}):\n\n"
        f"{_messages_payload(messages)}\n\n"
        "Escribe solo los bullets del resumen."
    )
    try:
        response = await llm.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": DIGEST_SYSTEM},
                {"role": "user", "content": user},
            ],
            max_tokens=DIGEST_MAX_TOKENS,
            temperature=0.3,
        )
        content = (response.choices[0].message.content or "").strip()
        # Some thinking models put text only in reasoning; keep a safe fallback.
        if not content:
            msg = response.choices[0].message
            reasoning = getattr(msg, "reasoning", None) or getattr(
                msg, "reasoning_content", None
            )
            if isinstance(reasoning, str):
                content = reasoning.strip()
    except Exception:
        logger.exception("Gmail digest LLM call failed")
        content = ""

    bullets = _parse_bullets(content)
    if not bullets:
        bullets = [
            f"{m.from_.split('<')[0].strip() or m.from_}: {m.subject}"
            for m in messages[:6]
        ]
        if not bullets:
            bullets = ["No pude resumir el correo ahora."]
    return InboxDigest(
        bullets=bullets,
        message_ids=[m.id for m in messages],
        created_at=time.time(),
        email=email,
    )


async def get_or_create_digest(
    *,
    gmail: GmailClient,
    llm: openai.AsyncOpenAI,
    storage_db_path: str,
    force: bool = False,
    query: str = "is:unread newer_than:2d",
    max_results: int = DIGEST_MAX_MESSAGES,
) -> dict[str, Any]:
    path = digest_path_for_db(storage_db_path)
    st = gmail.status()
    if not st.get("connected"):
        return {
            "ok": False,
            "error_code": "not_connected",
            "error": "Gmail no conectado.",
            "bullets": [],
            "messages": [],
        }
    if not st.get("gmail_ready"):
        return {
            "ok": False,
            "error_code": "needs_reconnect",
            "error": "Falta permiso de Gmail. Reconecta en Más → Gmail.",
            "bullets": [],
            "messages": [],
        }

    messages = await gmail.list_messages(query=query, max_results=max_results)
    ids = [m.id for m in messages]
    if not force:
        cached = cached_digest_for(path, ids)
        if cached is not None:
            return {
                "ok": True,
                "cached": True,
                "bullets": cached.bullets,
                "message_ids": cached.message_ids,
                "email": cached.email or st.get("email") or "",
                "messages": [
                    {
                        "id": m.id,
                        "subject": m.subject,
                        "from": m.from_,
                        "snippet": m.snippet,
                        "date": m.date,
                        "permalink": m.permalink,
                    }
                    for m in messages
                ],
            }

    digest = await generate_inbox_digest(
        llm, messages, email=str(st.get("email") or "")
    )
    save_digest(path, digest)
    logger.info(
        "Gmail digest generated bullets=%d msgs=%d",
        len(digest.bullets),
        len(messages),
    )
    return {
        "ok": True,
        "cached": False,
        "bullets": digest.bullets,
        "message_ids": digest.message_ids,
        "email": digest.email,
        "messages": [
            {
                "id": m.id,
                "subject": m.subject,
                "from": m.from_,
                "snippet": m.snippet,
                "date": m.date,
                "permalink": m.permalink,
            }
            for m in messages
        ],
    }
