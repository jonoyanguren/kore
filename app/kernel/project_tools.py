"""Tool to read whitelisted project documentation on demand."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from app.project_docs import list_allowed, read_doc

ToolHandler = Callable[[dict[str, Any]], Awaitable[str]]


def build_project_tools() -> tuple[list[dict], dict[str, ToolHandler]]:
    async def _list_project_docs(_args: dict[str, Any]) -> str:
        return "Documentos de proyecto legibles:\n" + list_allowed()

    async def _read_project_doc(args: dict[str, Any]) -> str:
        path = (args.get("path") or "").strip()
        if not path:
            return "Falta path. Usa list_project_docs para ver opciones."
        return read_doc(path)

    schemas = [
        {
            "type": "function",
            "function": {
                "name": "list_project_docs",
                "description": (
                    "List project markdown files this companion can read "
                    "(PLAN, TODO, QA, prompts, skills)."
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
                "name": "read_project_doc",
                "description": (
                    "Read a whitelisted project doc by path. "
                    "PLAN.md and TODO.md are already in the system prompt each turn; "
                    "use this for companion-plan, QA, or a specific prompt/skill file."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "e.g. docs/companion-plan.md or prompts/kimay.md",
                        }
                    },
                    "required": ["path"],
                    "additionalProperties": False,
                },
            },
        },
    ]
    handlers: dict[str, ToolHandler] = {
        "list_project_docs": _list_project_docs,
        "read_project_doc": _read_project_doc,
    }
    return schemas, handlers
