"""OpenAI-compatible tool definitions for the ClickUp integration.

Maps each tool schema to a handler that calls the corresponding
ClickUpClient method. Kept separate from clickup_client.py so the client
stays a plain API wrapper with no knowledge of the tool-calling format.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from app.integrations.clickup.clickup_client import ClickUpClient

ToolHandler = Callable[[dict[str, Any]], Awaitable[str]]


def build_clickup_tools(client: ClickUpClient) -> tuple[list[dict], dict[str, ToolHandler]]:
    """Return (tool schemas, handlers) for the ClickUp integration."""

    async def _list_workspaces(_: dict[str, Any]) -> str:
        workspaces = await client.list_workspaces()
        return str([{"id": w["id"], "name": w["name"]} for w in workspaces])

    async def _list_spaces(args: dict[str, Any]) -> str:
        spaces = await client.list_spaces(args["workspace_id"])
        return str([{"id": s["id"], "name": s["name"]} for s in spaces])

    async def _list_lists(args: dict[str, Any]) -> str:
        lists = await client.list_lists(args["space_id"])
        return str([{"id": l["id"], "name": l["name"]} for l in lists])

    async def _list_tasks(args: dict[str, Any]) -> str:
        tasks = await client.list_tasks(
            args["list_id"], include_closed=args.get("include_closed", False)
        )
        return str(
            [
                {
                    "id": t["id"],
                    "name": t["name"],
                    "status": t["status"]["status"],
                    "due_date": t.get("due_date"),
                    "priority": (t.get("priority") or {}).get("priority"),
                }
                for t in tasks
            ]
        )

    async def _create_task(args: dict[str, Any]) -> str:
        task = await client.create_task(
            list_id=args["list_id"],
            name=args["name"],
            description=args.get("description"),
            due_date_ms=args.get("due_date_ms"),
            priority=args.get("priority"),
        )
        return f"Tarea creada: {task['id']} - {task['name']}"

    async def _update_task(args: dict[str, Any]) -> str:
        task = await client.update_task(
            task_id=args["task_id"],
            name=args.get("name"),
            description=args.get("description"),
            status=args.get("status"),
            due_date_ms=args.get("due_date_ms"),
            priority=args.get("priority"),
        )
        return f"Tarea actualizada: {task['id']} - {task['name']} (status: {task['status']['status']})"

    schemas = [
        {
            "type": "function",
            "function": {
                "name": "list_clickup_workspaces",
                "description": (
                    "List the ClickUp workspaces (teams) the user has access to. "
                    "Call this first if you don't already know the workspace_id."
                ),
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_clickup_spaces",
                "description": "List spaces within a ClickUp workspace.",
                "parameters": {
                    "type": "object",
                    "properties": {"workspace_id": {"type": "string"}},
                    "required": ["workspace_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_clickup_lists",
                "description": "List task lists within a ClickUp space.",
                "parameters": {
                    "type": "object",
                    "properties": {"space_id": {"type": "string"}},
                    "required": ["space_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_clickup_tasks",
                "description": (
                    "List tasks in a ClickUp list, with their id, name, status, "
                    "due date and priority."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "list_id": {"type": "string"},
                        "include_closed": {
                            "type": "boolean",
                            "description": "Include already-closed/completed tasks. Default false.",
                        },
                    },
                    "required": ["list_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "create_clickup_task",
                "description": "Create a new task in a ClickUp list.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "list_id": {"type": "string"},
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "due_date_ms": {
                            "type": "integer",
                            "description": "Due date as Unix epoch milliseconds.",
                        },
                        "priority": {
                            "type": "integer",
                            "description": "1=urgent, 2=high, 3=normal, 4=low.",
                        },
                    },
                    "required": ["list_id", "name"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "update_clickup_task",
                "description": (
                    "Update a ClickUp task: rename, change description, change "
                    "status, due date, or priority. To close/complete a task, "
                    "set status to the list's terminal status name (e.g. "
                    "'complete' or 'closed') — check list_clickup_tasks first "
                    "if you don't know the exact status names used in this list."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string"},
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "status": {"type": "string"},
                        "due_date_ms": {"type": "integer"},
                        "priority": {"type": "integer"},
                    },
                    "required": ["task_id"],
                },
            },
        },
    ]

    handlers: dict[str, ToolHandler] = {
        "list_clickup_workspaces": _list_workspaces,
        "list_clickup_spaces": _list_spaces,
        "list_clickup_lists": _list_lists,
        "list_clickup_tasks": _list_tasks,
        "create_clickup_task": _create_task,
        "update_clickup_task": _update_task,
    }

    return schemas, handlers
