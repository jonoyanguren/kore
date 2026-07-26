"""Tools: authoritative Europe/Madrid clock and relative-date resolution."""

from __future__ import annotations

import json
from typing import Any, Awaitable, Callable

from app.timeutil import madrid_time_payload, resolve_date_payload

ToolHandler = Callable[[dict[str, Any]], Awaitable[str]]


def build_time_tools() -> tuple[list[dict], dict[str, ToolHandler]]:
    async def _get_madrid_time(_args: dict[str, Any]) -> str:
        return json.dumps(madrid_time_payload(), ensure_ascii=False)

    async def _resolve_madrid_date(args: dict[str, Any]) -> str:
        phrase = (args.get("phrase") or "").strip()
        if not phrase:
            return json.dumps(
                {"ok": "false", "error": "Falta phrase"}, ensure_ascii=False
            )
        return json.dumps(resolve_date_payload(phrase), ensure_ascii=False)

    schemas = [
        {
            "type": "function",
            "function": {
                "name": "get_madrid_time",
                "description": (
                    "Return the authoritative current date/time (Europe/Madrid calendar). "
                    "Call when you need 'now' or 'today'. "
                    "human = readable clock for /hora; date = YYYY-MM-DD for storage."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "resolve_madrid_date",
                "description": (
                    "Resolve a Spanish relative date phrase to YYYY-MM-DD and a "
                    "natural spoken form. Use for 'el lunes que viene', 'mañana', "
                    "'este viernes', etc. Store `date` (ISO); say `spoken` in chat "
                    "(never dump the full formal date unless asked)."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "phrase": {
                            "type": "string",
                            "description": (
                                "Relative phrase, e.g. 'el lunes que viene', "
                                "'mañana', 'este viernes'"
                            ),
                        }
                    },
                    "required": ["phrase"],
                    "additionalProperties": False,
                },
            },
        },
    ]
    handlers: dict[str, ToolHandler] = {
        "get_madrid_time": _get_madrid_time,
        "resolve_madrid_date": _resolve_madrid_date,
    }
    return schemas, handlers
