"""Format Gmail unread for morning dream payload."""

from __future__ import annotations

import logging

from app.integrations.gmail.client import GmailClient

logger = logging.getLogger(__name__)

DREAM_INBOX_MAX = 12


async def fetch_inbox_block_for_dream(gmail: GmailClient | None) -> str:
    """Return a plain-text block for the dream user payload."""
    if gmail is None:
        return "(Gmail no disponible en este proceso)"
    st = gmail.status()
    if not st.get("connected"):
        return "(Gmail no conectado — Más → Gmail)"
    if not st.get("gmail_ready"):
        return "(Gmail sin permiso gmail.modify — reconectar en Más → Gmail)"
    try:
        messages = await gmail.list_messages(
            query="is:unread newer_than:2d",
            max_results=DREAM_INBOX_MAX,
        )
    except Exception:
        logger.exception("Dream: failed listing Gmail inbox")
        return "(No se pudo leer el inbox ahora)"
    if not messages:
        return "(Sin unread recientes)"
    lines: list[str] = []
    for i, m in enumerate(messages, start=1):
        lines.append(
            f"{i}. de: {m.from_}\n"
            f"   asunto: {m.subject}\n"
            f"   snippet: {m.snippet}\n"
            f"   link: {m.permalink}"
        )
    email = st.get("email") or ""
    head = f"Cuenta: {email}\nUnread ({len(messages)}):\n" if email else f"Unread ({len(messages)}):\n"
    return head + "\n".join(lines)
