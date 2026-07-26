"""Thin REST wrapper over the ClickUp API v2.

Personal API token auth (never expires) — no OAuth flow needed for a
single-user personal assistant. Covers navigation (workspaces -> spaces ->
lists) and full task CRUD, which is the surface the tool-use layer exposes
to the model.
"""

from __future__ import annotations

import httpx

CLICKUP_API_BASE = "https://api.clickup.com/api/v2"

# ClickUp priority levels (documented mapping): 1=urgent, 2=high, 3=normal, 4=low.
PRIORITY_LEVELS = {"urgent": 1, "high": 2, "normal": 3, "low": 4}


class ClickUpClient:
    def __init__(self, api_token: str, http_client: httpx.AsyncClient) -> None:
        self._http = http_client
        # ClickUp personal tokens go directly in Authorization, no "Bearer" prefix.
        self._headers = {"Authorization": api_token}

    async def list_workspaces(self) -> list[dict]:
        response = await self._http.get(f"{CLICKUP_API_BASE}/team", headers=self._headers)
        response.raise_for_status()
        return response.json()["teams"]

    async def list_spaces(self, workspace_id: str) -> list[dict]:
        response = await self._http.get(
            f"{CLICKUP_API_BASE}/team/{workspace_id}/space", headers=self._headers
        )
        response.raise_for_status()
        return response.json()["spaces"]

    async def list_lists(self, space_id: str) -> list[dict]:
        response = await self._http.get(
            f"{CLICKUP_API_BASE}/space/{space_id}/list", headers=self._headers
        )
        response.raise_for_status()
        return response.json()["lists"]

    async def list_tasks(self, list_id: str, include_closed: bool = False) -> list[dict]:
        response = await self._http.get(
            f"{CLICKUP_API_BASE}/list/{list_id}/task",
            headers=self._headers,
            params={"include_closed": str(include_closed).lower()},
        )
        response.raise_for_status()
        return response.json()["tasks"]

    async def create_task(
        self,
        list_id: str,
        name: str,
        description: str | None = None,
        due_date_ms: int | None = None,
        priority: int | None = None,
    ) -> dict:
        body: dict = {"name": name}
        if description is not None:
            body["description"] = description
        if due_date_ms is not None:
            body["due_date"] = due_date_ms
        if priority is not None:
            body["priority"] = priority
        response = await self._http.post(
            f"{CLICKUP_API_BASE}/list/{list_id}/task", headers=self._headers, json=body
        )
        response.raise_for_status()
        return response.json()

    async def update_task(
        self,
        task_id: str,
        name: str | None = None,
        description: str | None = None,
        status: str | None = None,
        due_date_ms: int | None = None,
        priority: int | None = None,
    ) -> dict:
        """Also used to close/complete a task: pass `status` set to the
        list's terminal status name (e.g. "complete", "closed", "done") —
        this varies per list/workspace, so the caller should look it up via
        `list_tasks`/`list_lists` rather than assume a fixed string.
        """
        body: dict = {}
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if status is not None:
            body["status"] = status
        if due_date_ms is not None:
            body["due_date"] = due_date_ms
        if priority is not None:
            body["priority"] = priority
        response = await self._http.put(
            f"{CLICKUP_API_BASE}/task/{task_id}", headers=self._headers, json=body
        )
        response.raise_for_status()
        return response.json()
