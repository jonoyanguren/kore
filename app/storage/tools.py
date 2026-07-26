"""OpenAI-compatible tool definitions for the notes memory store."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from app.storage.memory import MemoryStore

ToolHandler = Callable[[dict[str, Any]], Awaitable[str]]


def build_memory_tools(store: MemoryStore) -> tuple[list[dict], dict[str, ToolHandler]]:
    """Return (tool schemas, handlers) for saving/removing durable notes."""

    async def _remember_note(args: dict[str, Any]) -> str:
        note_id = await store.add_note(args["text"])
        return f"Nota guardada (id {note_id})."

    async def _forget_note(args: dict[str, Any]) -> str:
        deleted = await store.delete_note(int(args["note_id"]))
        return "Nota eliminada." if deleted else "No encontré esa nota."

    schemas = [
        {
            "type": "function",
            "function": {
                "name": "remember_note",
                "description": (
                    "Save a short durable fact or piece of context that should "
                    "be remembered in every future conversation (e.g. naming "
                    "conventions, preferences, what a given list/project is "
                    "for). Use when the user says things like 'recuerda que...' "
                    "or clearly wants something noted for the future."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {"text": {"type": "string"}},
                    "required": ["text"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "forget_note",
                "description": "Delete a previously saved note by its id.",
                "parameters": {
                    "type": "object",
                    "properties": {"note_id": {"type": "integer"}},
                    "required": ["note_id"],
                },
            },
        },
    ]

    handlers: dict[str, ToolHandler] = {
        "remember_note": _remember_note,
        "forget_note": _forget_note,
    }

    return schemas, handlers
