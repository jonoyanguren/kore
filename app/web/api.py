"""HTTP API for the web console: auth + tasks + chat."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field

from app.storage.memory import TaskRow, VALID_TASK_STATUSES
from app.storage.task_tools import sync_tasks_vault
from app.web.auth import (
    COOKIE_NAME,
    console_secret_configured,
    require_console_auth,
)
from app.web.auth import _secrets_match

router = APIRouter(prefix="/api", tags=["console"])

TaskStatus = Literal["open", "in_progress", "done", "cancelled"]


class LoginBody(BaseModel):
    secret: str


class TaskOut(BaseModel):
    id: int
    title: str
    status: str
    due_at: str | None = None
    priority: int = 0
    notes: str | None = None
    url: str | None = None
    project: str | None = None

    @classmethod
    def from_row(cls, row: TaskRow) -> TaskOut:
        return cls(
            id=row.id,
            title=row.title,
            status=row.status,
            due_at=row.due_at,
            priority=row.priority,
            notes=row.notes,
            url=row.url,
            project=row.project,
        )


class CreateTaskBody(BaseModel):
    title: str = Field(min_length=1)
    status: TaskStatus = "open"
    due_at: str | None = None
    priority: int = 0
    notes: str | None = None
    url: str | None = None
    project: str | None = None


class PatchTaskBody(BaseModel):
    title: str | None = None
    status: TaskStatus | None = None
    due_at: str | None = None
    priority: int | None = None
    notes: str | None = None
    url: str | None = None
    project: str | None = None
    clear_due: bool = False
    clear_url: bool = False
    clear_notes: bool = False
    clear_project: bool = False


def _task_dict(row: TaskRow) -> dict[str, Any]:
    return TaskOut.from_row(row).model_dump()


@router.post("/login")
async def login(body: LoginBody, request: Request, response: Response) -> dict[str, bool]:
    expected = console_secret_configured()
    if not _secrets_match(body.secret.strip(), expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")
    response.set_cookie(
        key=COOKIE_NAME,
        value=body.secret.strip(),
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
        max_age=60 * 60 * 24 * 30,
        path="/",
    )
    return {"ok": True}


@router.post("/logout")
async def logout(response: Response) -> dict[str, bool]:
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/me", dependencies=[Depends(require_console_auth)])
async def me() -> dict[str, bool]:
    return {"ok": True}


@router.get("/tasks", dependencies=[Depends(require_console_auth)])
async def list_tasks(
    request: Request,
    status_filter: Annotated[str, Query(alias="status")] = "open",
    project: str | None = None,
    limit: int = 50,
) -> dict[str, list[dict[str, Any]]]:
    rows = await request.app.state.memory.list_tasks(
        status=status_filter,
        limit=min(limit, 100),
        project=project,
    )
    return {"tasks": [_task_dict(r) for r in rows]}


@router.post("/tasks", dependencies=[Depends(require_console_auth)])
async def create_task(request: Request, body: CreateTaskBody) -> dict[str, Any]:
    if body.status not in VALID_TASK_STATUSES:
        raise HTTPException(status_code=400, detail="invalid status")
    task_id = await request.app.state.memory.add_task(
        title=body.title,
        due_at=body.due_at,
        priority=body.priority,
        notes=body.notes,
        url=body.url,
        project=body.project,
        status=body.status,
    )
    await sync_tasks_vault(request.app.state.memory, request.app.state.vault)
    task = await request.app.state.memory.get_task(task_id)
    assert task is not None
    return {"task": _task_dict(task)}


@router.patch("/tasks/{task_id}", dependencies=[Depends(require_console_auth)])
async def patch_task(
    request: Request, task_id: int, body: PatchTaskBody
) -> dict[str, Any]:
    ok = await request.app.state.memory.update_task(
        task_id,
        title=body.title,
        status=body.status,
        due_at=body.due_at,
        priority=body.priority,
        notes=body.notes,
        url=body.url,
        project=body.project,
        clear_due=body.clear_due,
        clear_url=body.clear_url,
        clear_notes=body.clear_notes,
        clear_project=body.clear_project,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="task not found")
    await sync_tasks_vault(request.app.state.memory, request.app.state.vault)
    task = await request.app.state.memory.get_task(task_id)
    assert task is not None
    return {"task": _task_dict(task)}


@router.post("/tasks/{task_id}/complete", dependencies=[Depends(require_console_auth)])
async def complete_task(request: Request, task_id: int) -> dict[str, Any]:
    ok = await request.app.state.memory.complete_task(task_id)
    if not ok:
        raise HTTPException(status_code=404, detail="task not found")
    await sync_tasks_vault(request.app.state.memory, request.app.state.vault)
    task = await request.app.state.memory.get_task(task_id)
    assert task is not None
    return {"task": _task_dict(task)}


@router.delete("/tasks/{task_id}", dependencies=[Depends(require_console_auth)])
async def delete_task(request: Request, task_id: int) -> dict[str, Any]:
    ok = await request.app.state.memory.delete_task(task_id)
    if not ok:
        raise HTTPException(status_code=404, detail="task not found")
    await sync_tasks_vault(request.app.state.memory, request.app.state.vault)
    return {"ok": True}


class ChatBody(BaseModel):
    text: str = Field(min_length=1, max_length=8000)


@router.get("/messages", dependencies=[Depends(require_console_auth)])
async def list_messages(
    request: Request,
    limit: int = 80,
) -> dict[str, list[dict[str, str]]]:
    rows = await request.app.state.memory.list_messages_for_day(
        limit=min(max(limit, 1), 200)
    )
    return {"messages": [{"role": role, "content": content} for role, content in rows]}


@router.post("/chat", dependencies=[Depends(require_console_auth)])
async def chat(request: Request, body: ChatBody) -> dict[str, str]:
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="empty text")
    llm = getattr(request.app.state, "llm", None)
    if llm is None:
        raise HTTPException(status_code=503, detail="llm not ready")
    reply = await llm.ask(text)
    return {"reply": reply}
