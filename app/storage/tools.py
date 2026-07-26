"""OpenAI-compatible tool definitions for memory and diary."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from app.storage.memory import MemoryStore
from app.storage.vault import Vault
from app.timeutil import session_date_str

ToolHandler = Callable[[dict[str, Any]], Awaitable[str]]


def build_memory_tools(
    store: MemoryStore, vault: Vault | None = None
) -> tuple[list[dict], dict[str, ToolHandler]]:
    """Return (tool schemas, handlers) for categorical memory + diary."""

    async def _save_memory(args: dict[str, Any]) -> str:
        item_id = await store.save_memory(
            category=args.get("category", "general"),
            text=args["text"],
        )
        category = (args.get("category") or "general").strip().lower()
        if vault is not None:
            vault.append_memory(category, item_id, args["text"])
        return f"Memoria guardada en '{category}' (id {item_id})."

    async def _add_diary_entry(args: dict[str, Any]) -> str:
        day = args.get("day") or session_date_str()
        entry_id = await store.add_diary_entry(text=args["text"], day=day)
        if vault is not None:
            vault.append_diary(day, entry_id, args["text"])
        return f"Entrada de diario guardada (id {entry_id})."

    async def _forget_memory(args: dict[str, Any]) -> str:
        deleted = await store.delete_memory(int(args["memory_id"]))
        return "Memoria eliminada." if deleted else "No encontré esa memoria."

    # Legacy aliases — same handlers under old names so older prompts still work.
    async def _remember_note(args: dict[str, Any]) -> str:
        return await _save_memory({"category": "general", "text": args["text"]})

    async def _forget_note(args: dict[str, Any]) -> str:
        return await _forget_memory({"memory_id": args["note_id"]})

    schemas = [
        {
            "type": "function",
            "function": {
                "name": "save_memory",
                "description": (
                    "Save a durable fact about the user under a category "
                    "(work, people, projects, health, preferences, general, …). "
                    "Use when something should be remembered across days."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "Category slug, e.g. work, people, projects",
                        },
                        "text": {
                            "type": "string",
                            "description": "Short durable fact to remember",
                        },
                    },
                    "required": ["category", "text"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "add_diary_entry",
                "description": (
                    "Append something that happened today (or a given day) to the diary. "
                    "Use for day events, not long-term preferences."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "day": {
                            "type": "string",
                            "description": "YYYY-MM-DD in Europe/Madrid; defaults to today",
                        },
                    },
                    "required": ["text"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "forget_memory",
                "description": "Delete a previously saved memory item by id.",
                "parameters": {
                    "type": "object",
                    "properties": {"memory_id": {"type": "integer"}},
                    "required": ["memory_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "remember_note",
                "description": (
                    "Legacy alias for save_memory with category=general. "
                    "Prefer save_memory with an explicit category."
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
                "description": "Legacy alias for forget_memory.",
                "parameters": {
                    "type": "object",
                    "properties": {"note_id": {"type": "integer"}},
                    "required": ["note_id"],
                },
            },
        },
    ]

    handlers: dict[str, ToolHandler] = {
        "save_memory": _save_memory,
        "add_diary_entry": _add_diary_entry,
        "forget_memory": _forget_memory,
        "remember_note": _remember_note,
        "forget_note": _forget_note,
    }

    return schemas, handlers
