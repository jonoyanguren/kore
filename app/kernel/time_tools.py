"""Tool: authoritative Europe/Madrid clock (never let the model guess time)."""

from __future__ import annotations

import json
from typing import Any, Awaitable, Callable

from app.timeutil import madrid_time_payload

ToolHandler = Callable[[dict[str, Any]], Awaitable[str]]


def build_time_tools() -> tuple[list[dict], dict[str, ToolHandler]]:
    async def _get_madrid_time(_args: dict[str, Any]) -> str:
        return json.dumps(madrid_time_payload(), ensure_ascii=False)

    schemas = [
        {
            "type": "function",
            "function": {
                "name": "get_madrid_time",
                "description": (
                    "Return the authoritative current date/time in Europe/Madrid. "
                    "Call this whenever you need 'now', 'today', deadlines, "
                    "relative days (mañana, el viernes), or diary days — "
                    "never invent or assume the clock."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            },
        }
    ]
    handlers: dict[str, ToolHandler] = {"get_madrid_time": _get_madrid_time}
    return schemas, handlers
