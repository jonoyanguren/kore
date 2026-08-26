"""LLM tools for Gmail inbox (list, mark read, triage log)."""

from __future__ import annotations

import json
from typing import Any

from app.config import settings
from app.integrations.gmail.client import (
    GmailApiError,
    GmailClient,
    GmailConfigError,
    GmailNotConnectedError,
)
from app.integrations.gmail.triage_log import (
    list_marked_read,
    marked_read_path_for_db,
    today_madrid_start_unix,
)
from app.llm.llm_assistant import ToolHandler


def build_gmail_tools(
    gmail: GmailClient | None,
) -> tuple[list[dict[str, Any]], dict[str, ToolHandler]]:
    if gmail is None:
        return [], {}

    schemas: list[dict[str, Any]] = [
        {
            "type": "function",
            "function": {
                "name": "list_inbox",
                "description": (
                    "Lista correos de Gmail (por defecto unread recientes). "
                    "Usa query Gmail search (is:unread, newer_than:1d, from:…)."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Gmail search query. Default: is:unread newer_than:1d",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Máximo mensajes (1–25). Default 10.",
                        },
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "mark_email_read",
                "description": (
                    "Marca un correo Gmail como leído (quita UNREAD) y lo anota "
                    "en el log de triage por si Jon quiere revisarlo después."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message_id": {
                            "type": "string",
                            "description": "Id del mensaje Gmail (de list_inbox).",
                        },
                    },
                    "required": ["message_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_marked_read",
                "description": (
                    "Lista correos que Kore marcó como leídos (triage log). "
                    "Útil si Jon pregunta qué se marcó leído hoy / recientemente."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Máximo entradas (1–50). Default 20.",
                        },
                        "today_only": {
                            "type": "boolean",
                            "description": "Si true, solo desde medianoche Madrid. Default true.",
                        },
                    },
                },
            },
        },
    ]

    async def list_inbox(args: dict[str, Any]) -> str:
        query = str(args.get("query") or "is:unread newer_than:1d").strip()
        max_results = int(args.get("max_results") or 10)
        max_results = max(1, min(max_results, 25))
        try:
            messages = await gmail.list_messages(query=query, max_results=max_results)
        except GmailNotConnectedError:
            return json.dumps(
                {
                    "ok": False,
                    "error": "gmail_not_connected",
                    "hint": "Conecta Gmail desde Más → Gmail en la consola.",
                }
            )
        except GmailConfigError as exc:
            return json.dumps({"ok": False, "error": "gmail_not_configured", "detail": str(exc)})
        except GmailApiError as exc:
            return json.dumps({"ok": False, "error": exc.code, "detail": exc.message})
        except Exception as exc:
            return json.dumps({"ok": False, "error": "gmail_api_error", "detail": str(exc)})
        return json.dumps(
            {
                "ok": True,
                "query": query,
                "count": len(messages),
                "messages": [
                    {
                        "id": m.id,
                        "subject": m.subject,
                        "from": m.from_,
                        "snippet": m.snippet,
                        "date": m.date,
                        "unread": m.unread,
                        "permalink": m.permalink,
                    }
                    for m in messages
                ],
            },
            ensure_ascii=False,
        )

    async def mark_email_read(args: dict[str, Any]) -> str:
        message_id = str(args.get("message_id") or "").strip()
        if not message_id:
            return json.dumps({"ok": False, "error": "message_id_required"})
        try:
            ok = await gmail.mark_read(message_id, reason="tool")
        except GmailNotConnectedError:
            return json.dumps({"ok": False, "error": "gmail_not_connected"})
        except GmailConfigError as exc:
            return json.dumps({"ok": False, "error": "gmail_not_configured", "detail": str(exc)})
        except GmailApiError as exc:
            return json.dumps({"ok": False, "error": exc.code, "detail": exc.message})
        except Exception as exc:
            return json.dumps({"ok": False, "error": "gmail_api_error", "detail": str(exc)})
        return json.dumps({"ok": ok, "message_id": message_id, "logged": True})

    async def list_marked_read_tool(args: dict[str, Any]) -> str:
        limit = int(args.get("limit") or 20)
        limit = max(1, min(limit, 50))
        today_only = args.get("today_only")
        if today_only is None:
            today_only = True
        since = today_madrid_start_unix() if today_only else None
        from app.accounts.context import active_db_path

        entries = list_marked_read(
            marked_read_path_for_db(active_db_path(settings.storage_db_path)),
            limit=limit,
            since=since,
        )
        return json.dumps(
            {
                "ok": True,
                "today_only": bool(today_only),
                "count": len(entries),
                "entries": entries,
            },
            ensure_ascii=False,
        )

    handlers: dict[str, ToolHandler] = {
        "list_inbox": list_inbox,
        "mark_email_read": mark_email_read,
        "list_marked_read": list_marked_read_tool,
    }
    return schemas, handlers
