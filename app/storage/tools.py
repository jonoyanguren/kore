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

    def _store() -> MemoryStore:
        from app.accounts.context import current_memory

        return current_memory.get() or store

    def _vault() -> Vault | None:
        from app.accounts.context import current_vault

        return current_vault.get() or vault

    async def _save_memory(args: dict[str, Any]) -> str:
        item_id = await _store().save_memory(
            category=args.get("category", "general"),
            text=args["text"],
        )
        category = (args.get("category") or "general").strip().lower()
        v = _vault()
        if v is not None:
            v.append_memory(category, item_id, args["text"])
        return f"Memoria guardada en '{category}' (id {item_id})."

    async def _add_diary_entry(args: dict[str, Any]) -> str:
        day = args.get("day") or session_date_str()
        entry_id = await _store().add_diary_entry(text=args["text"], day=day)
        v = _vault()
        if v is not None:
            v.append_diary(day, entry_id, args["text"])
        return f"Entrada de diario guardada (id {entry_id})."

    async def _forget_memory(args: dict[str, Any]) -> str:
        deleted = await _store().delete_memory(int(args["memory_id"]))
        return "Memoria eliminada." if deleted else "No encontré esa memoria."

    async def _list_memory(args: dict[str, Any]) -> str:
        category = (args.get("category") or "").strip().lower() or None
        try:
            limit = int(args.get("limit") or 40)
        except (TypeError, ValueError):
            limit = 40
        limit = max(1, min(limit, 80))
        rows = await _store().list_memory(category=category, limit=limit)
        if not rows:
            scope = f"categoría '{category}'" if category else "memoria"
            return f"No hay items en {scope}."
        lines = [
            f"- (id {mid}) [{cat}] {text}" for mid, cat, text in rows
        ]
        header = (
            f"Memoria ({category}, {len(rows)}):"
            if category
            else f"Memoria reciente ({len(rows)}):"
        )
        return header + "\n" + "\n".join(lines)

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
                "name": "list_memory",
                "description": (
                    "List durable memory items from the vault/SQLite "
                    "(optionally one category). Use to find thin or missing context "
                    "before asking interview questions — not for task board status."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": (
                                "Optional slug: work, people, projects, health, "
                                "preferences, general, … Omit for recent across all."
                            ),
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Max items (default 40, max 80)",
                        },
                    },
                    "additionalProperties": False,
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
        "list_memory": _list_memory,
        "add_diary_entry": _add_diary_entry,
        "forget_memory": _forget_memory,
        "remember_note": _remember_note,
        "forget_note": _forget_note,
    }

    return schemas, handlers


async def format_memory_excerpt(
    store: MemoryStore, *, max_chars: int = 3500
) -> str:
    """Compact digest for mission prompts — not the whole vault."""
    digests = await store.memory_digests(limit_per_category=8)
    if not digests:
        return ""
    lines: list[str] = []
    for category, items in digests.items():
        if not items:
            continue
        lines.append(f"### {category}")
        for item_id, text in items:
            t = (text or "").strip().replace("\n", " ")
            if len(t) > 280:
                t = t[:277] + "…"
            lines.append(f"- (id {item_id}) {t}")
    blob = "\n".join(lines).strip()
    if len(blob) > max_chars:
        blob = blob[: max_chars - 1] + "…"
    return blob


def build_mission_tools(
    store: MemoryStore, vault: Vault | None = None
) -> tuple[list[dict], dict[str, ToolHandler]]:
    """Web search + read-only memory. Missions must not write vault/SQLite."""
    from app.integrations.web.tools import build_web_tools

    web_schemas, web_handlers = build_web_tools()
    mem_schemas, mem_handlers = build_memory_tools(store, vault)
    read_names = {"list_memory"}
    mem_schemas = [
        s for s in mem_schemas if s["function"]["name"] in read_names
    ]
    mem_handlers = {n: h for n, h in mem_handlers.items() if n in read_names}
    return web_schemas + mem_schemas, {**web_handlers, **mem_handlers}
