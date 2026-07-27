"""Tools for local tasks and agenda."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from app.storage.memory import MemoryStore, format_task_lines, format_tasks_message
from app.storage.vault import Vault
from app.timeutil import session_date_str

ToolHandler = Callable[[dict[str, Any]], Awaitable[str]]


async def sync_tasks_vault(store: MemoryStore, vault: Vault) -> None:
    """Rewrite vault/tasks/open.md from active SQLite tasks."""
    rows = await store.list_tasks(status="open", limit=100)
    vault.write_tasks(
        format_task_lines(rows, detailed=True)
        or ["(ninguna abierta)"]
    )


async def purge_done_tasks_archiving(store: MemoryStore, vault: Vault) -> int:
    """Archive done tasks to vault/tasks/done.md, then hard-delete from SQLite."""
    rows = await store.list_and_purge_done_tasks()
    if not rows:
        return 0
    vault.append_done_tasks(
        session_date_str(),
        format_task_lines(rows, detailed=True),
    )
    await sync_tasks_vault(store, vault)
    return len(rows)


def build_task_tools(
    store: MemoryStore, vault: Vault
) -> tuple[list[dict], dict[str, ToolHandler]]:
    async def _add_task(args: dict[str, Any]) -> str:
        task_id = await store.add_task(
            title=args["title"],
            due_at=args.get("due_at"),
            priority=int(args.get("priority") or 0),
            notes=args.get("notes"),
            url=args.get("url"),
            project=args.get("project"),
            status=args.get("status") or "open",
        )
        await sync_tasks_vault(store, vault)
        task = await store.get_task(task_id)
        assert task is not None
        body = "\n".join(format_task_lines([task], detailed=True))
        return f"Creada.\n\n{body}"

    async def _list_tasks(args: dict[str, Any]) -> str:
        status = args.get("status", "open")
        if status == "all":
            status = "all"
        rows = await store.list_tasks(
            status=status,
            limit=int(args.get("limit") or 30),
            project=args.get("project"),
        )
        heading = "Tareas"
        if status == "open":
            heading = "Tareas"
        elif status and status != "all":
            heading = f"Tareas ({status})"
        return format_tasks_message(rows, heading=heading)

    async def _get_task(args: dict[str, Any]) -> str:
        task = await store.get_task(int(args["task_id"]))
        if task is None:
            return "No encontré esa tarea."
        return "\n".join(format_task_lines([task], detailed=True))

    async def _update_task(args: dict[str, Any]) -> str:
        ok = await store.update_task(
            int(args["task_id"]),
            title=args.get("title"),
            status=args.get("status"),
            due_at=args.get("due_at"),
            priority=int(args["priority"]) if args.get("priority") is not None else None,
            notes=args.get("notes"),
            url=args.get("url"),
            project=args.get("project"),
            clear_due=bool(args.get("clear_due")),
            clear_url=bool(args.get("clear_url")),
            clear_notes=bool(args.get("clear_notes")),
            clear_project=bool(args.get("clear_project")),
        )
        if not ok:
            return "No pude actualizar esa tarea."
        await sync_tasks_vault(store, vault)
        task = await store.get_task(int(args["task_id"]))
        assert task is not None
        return "Actualizada.\n\n" + "\n".join(
            format_task_lines([task], detailed=True)
        )

    async def _complete_task(args: dict[str, Any]) -> str:
        ok = await store.complete_task(int(args["task_id"]))
        if ok:
            await sync_tasks_vault(store, vault)
        return "Tarea marcada como hecha." if ok else "No encontré esa tarea."

    async def _delete_task(args: dict[str, Any]) -> str:
        ok = await store.delete_task(int(args["task_id"]))
        if ok:
            await sync_tasks_vault(store, vault)
        return "Tarea eliminada (cancelada)." if ok else "No encontré esa tarea."

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
                "description": (
                    "Create a local personal task in SQLite (not ClickUp). "
                    "If the user pasted a URL (Instagram, YouTube, doc…), ALWAYS set url. "
                    "Use notes for extra context. Always set project when the "
                    "topic is clear (kore, kimay, personal, lol, …) — infer from "
                    "conversation; there is no UI space picker."
                ),
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
                        "url": {
                            "type": "string",
                            "description": "Link related to the task (http/https)",
                        },
                        "project": {
                            "type": "string",
                            "description": (
                                "Inferred slug: kore, kimay, personal, lol, … "
                                "Omit only if unclear."
                            ),
                        },
                        "status": {
                            "type": "string",
                            "description": "open|in_progress|done|cancelled (default open)",
                        },
                    },
                    "required": ["title"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_tasks",
                "description": (
                    "List local tasks. status=open (includes in_progress)|"
                    "in_progress|done|cancelled|all. Optional project filter."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string"},
                        "project": {"type": "string"},
                        "limit": {"type": "integer"},
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_task",
                "description": "Show one task with notes and link by id.",
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
                "name": "update_task",
                "description": (
                    "Update fields on a task (title, status, due, notes, url, project). "
                    "Use clear_* flags to wipe optional fields."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "integer"},
                        "title": {"type": "string"},
                        "status": {"type": "string"},
                        "due_at": {"type": "string"},
                        "priority": {"type": "integer"},
                        "notes": {"type": "string"},
                        "url": {"type": "string"},
                        "project": {"type": "string"},
                        "clear_due": {"type": "boolean"},
                        "clear_url": {"type": "boolean"},
                        "clear_notes": {"type": "boolean"},
                        "clear_project": {"type": "boolean"},
                    },
                    "required": ["task_id"],
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
                "name": "delete_task",
                "description": "Cancel/delete a task by id (soft delete).",
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
        "get_task": _get_task,
        "update_task": _update_task,
        "complete_task": _complete_task,
        "delete_task": _delete_task,
        "add_agenda_item": _add_agenda_item,
        "list_agenda": _list_agenda,
    }
    return schemas, handlers
