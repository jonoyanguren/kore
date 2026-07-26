"""Tools for local tasks and agenda."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from app.storage.memory import MemoryStore
from app.storage.vault import Vault
from app.timeutil import session_date_str

ToolHandler = Callable[[dict[str, Any]], Awaitable[str]]


def build_task_tools(
    store: MemoryStore, vault: Vault
) -> tuple[list[dict], dict[str, ToolHandler]]:
    async def _add_task(args: dict[str, Any]) -> str:
        task_id = await store.add_task(
            title=args["title"],
            due_at=args.get("due_at"),
            priority=int(args.get("priority") or 0),
            notes=args.get("notes"),
        )
        due = args.get("due_at") or "sin fecha"
        return f"Tarea creada (id {task_id}): {args['title'].strip()} — {due}."

    async def _list_tasks(args: dict[str, Any]) -> str:
        status = args.get("status", "open")
        if status == "all":
            status = None
        rows = await store.list_tasks(status=status, limit=int(args.get("limit") or 20))
        if not rows:
            return "No hay tareas" + (f" con status={args.get('status', 'open')}." if status else ".")
        lines = []
        for task_id, title, st, due_at, priority in rows:
            due = due_at or "—"
            lines.append(f"- (id {task_id}) [{st}] {title} (due {due}, prio {priority})")
        return "Tareas:\n" + "\n".join(lines)

    async def _complete_task(args: dict[str, Any]) -> str:
        ok = await store.complete_task(int(args["task_id"]))
        return "Tarea marcada como hecha." if ok else "No encontré esa tarea abierta."

    async def _add_agenda_item(args: dict[str, Any]) -> str:
        item_id = await store.add_agenda_item(
            title=args["title"],
            starts_at=args["starts_at"],
            ends_at=args.get("ends_at"),
        )
        month = args["starts_at"][:7]
        rows = await store.list_agenda_for_month(month)
        vault.write_agenda_month(
            month,
            [
                f"- (id {i}) {starts} — {title} [{st}]"
                for i, starts, title, st in rows
            ],
        )
        return f"Agenda: {args['title'].strip()} el {args['starts_at']} (id {item_id})."

    async def _list_agenda(args: dict[str, Any]) -> str:
        from_day = args.get("from_day") or session_date_str()
        rows = await store.list_agenda_upcoming(
            from_day=from_day, limit=int(args.get("limit") or 15)
        )
        if not rows:
            return f"Nada en agenda desde {from_day}."
        lines = [
            f"- (id {i}) {starts} — {title} [{st}]"
            for i, starts, title, st in rows
        ]
        return "Agenda:\n" + "\n".join(lines)

    schemas = [
        {
            "type": "function",
            "function": {
                "name": "add_task",
                "description": "Create a local personal task (not ClickUp).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "due_at": {
                            "type": "string",
                            "description": "YYYY-MM-DD optional",
                        },
                        "priority": {
                            "type": "integer",
                            "description": "Higher = more important; default 0",
                        },
                        "notes": {"type": "string"},
                    },
                    "required": ["title"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_tasks",
                "description": "List local tasks. status=open|done|all.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string"},
                        "limit": {"type": "integer"},
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "complete_task",
                "description": "Mark a local task done by id.",
                "parameters": {
                    "type": "object",
                    "properties": {"task_id": {"type": "integer"}},
                    "required": ["task_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "add_agenda_item",
                "description": (
                    "Add a calendar/agenda event (appointment, reminder). "
                    "starts_at as YYYY-MM-DD or YYYY-MM-DDTHH:MM (Europe/Madrid)."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "starts_at": {"type": "string"},
                        "ends_at": {"type": "string"},
                    },
                    "required": ["title", "starts_at"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_agenda",
                "description": "List upcoming agenda items from a day (default today).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "from_day": {"type": "string"},
                        "limit": {"type": "integer"},
                    },
                },
            },
        },
    ]

    handlers: dict[str, ToolHandler] = {
        "add_task": _add_task,
        "list_tasks": _list_tasks,
        "complete_task": _complete_task,
        "add_agenda_item": _add_agenda_item,
        "list_agenda": _list_agenda,
    }
    return schemas, handlers
