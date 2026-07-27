"""HTTP API for the web console: auth + tasks + chat."""

from __future__ import annotations

import re
from datetime import timedelta
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.storage.memory import TaskRow, VALID_TASK_STATUSES, format_tasks_message
from app.storage.task_tools import sync_tasks_vault
from app.timeutil import (
    format_madrid_clock,
    format_relative_es,
    now_madrid,
    session_date_str,
    today_madrid,
)
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


def _dream_excerpt(raw: str | None, *, max_len: int = 320) -> str | None:
    if not raw:
        return None
    lines = []
    for line in raw.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        lines.append(s)
    text = " ".join(lines).strip()
    if not text:
        return None
    if len(text) > max_len:
        return text[: max_len - 1].rstrip() + "…"
    return text


@router.get("/day", dependencies=[Depends(require_console_auth)])
async def day_snapshot(request: Request) -> dict[str, Any]:
    """Day strip: clock, open task counts, agenda, latest dream excerpt."""
    memory = request.app.state.memory
    vault = request.app.state.vault
    today = session_date_str()
    clock = format_madrid_clock()
    weekday = clock.split(",")[0]  # "lunes 27 de julio de 2026"

    open_tasks = await memory.list_tasks(status="open", limit=100)
    n_progress = sum(1 for t in open_tasks if t.status == "in_progress")
    n_pending = sum(1 for t in open_tasks if t.status == "open")

    agenda_rows = await memory.list_agenda_upcoming(from_day=today, limit=5)
    agenda = [
        {
            "id": i,
            "starts_at": starts,
            "title": title,
            "status": st,
        }
        for i, starts, title, st in agenda_rows
    ]

    yesterday = (today_madrid() - timedelta(days=1)).isoformat()
    dream_day = yesterday
    dream_raw = vault.read_dream(yesterday)
    if dream_raw is None:
        dream_day = today
        dream_raw = vault.read_dream(today)
    dream = _dream_excerpt(dream_raw)

    return {
        "today": today,
        "clock": clock,
        "headline": weekday,
        "tasks": {"in_progress": n_progress, "open": n_pending},
        "agenda": agenda,
        "dream": (
            {"day": dream_day, "excerpt": dream} if dream else None
        ),
        "server_now": now_madrid().isoformat(),
    }


@router.get("/messages", dependencies=[Depends(require_console_auth)])
async def list_messages(
    request: Request,
    limit: int = 10,
    before: int | None = None,
) -> dict[str, Any]:
    page = min(max(limit, 1), 50)
    memory = request.app.state.memory
    rows = await memory.list_recent_messages(limit=page, before_id=before)

    if before is not None:
        has_more = (
            bool(rows) and (await memory.count_messages_before(rows[0][0])) > 0
        )
    else:
        total = await memory.count_messages()
        has_more = total > len(rows)

    # Resolve task ids mentioned in content for rich cards
    task_ids: set[int] = set()

    id_re = re.compile(
        r"(?:tarea|task|id)\s*#?\s*(\d+)|\b(\d+)\.\s+\S",
        re.IGNORECASE,
    )
    for _mid, _role, content, _ts in rows:
        for m in id_re.finditer(content or ""):
            for g in m.groups():
                if g:
                    task_ids.add(int(g))
    tasks_by_id: dict[int, dict[str, Any]] = {}
    for tid in task_ids:
        row = await memory.get_task(tid)
        if row is not None:
            tasks_by_id[tid] = _task_dict(row)

    out: list[dict[str, Any]] = []
    for mid, role, content, created_at in rows:
        mentioned = []
        for m in id_re.finditer(content or ""):
            for g in m.groups():
                if g and int(g) in tasks_by_id:
                    t = tasks_by_id[int(g)]
                    if t not in mentioned:
                        mentioned.append(t)
        out.append(
            {
                "id": mid,
                "role": role,
                "content": content,
                "created_at": created_at,
                "relative": format_relative_es(created_at),
                "tasks": mentioned,
            }
        )
    return {"messages": out, "has_more": has_more}


async def _persist_exchange(memory: Any, user: str, assistant: str) -> None:
    await memory.add_message("user", user)
    await memory.add_message("assistant", assistant)


async def _run_chat(
    request: Request,
    text: str,
    *,
    on_status: Any | None = None,
) -> dict[str, Any]:
    """Shared chat handler for JSON and SSE endpoints."""

    async def status(msg: str) -> None:
        if on_status is None:
            return
        await on_status(msg)

    memory = request.app.state.memory
    cmd = text.split()[0].lower() if text.startswith("/") else ""

    if cmd in ("/tareas", "/tasks"):
        await status("Listando tareas…")
        rows = await memory.list_tasks(status="open", limit=40)
        reply = format_tasks_message(rows, heading="Tareas")
        await _persist_exchange(memory, text, reply)
        return {
            "reply": reply,
            "tasks_created": [],
            "tasks_listed": [_task_dict(t) for t in rows],
            "tasks_changed": False,
        }
    if cmd == "/hora":
        await status("Mirando el reloj…")
        reply = format_madrid_clock()
        await _persist_exchange(memory, text, reply)
        return {
            "reply": reply,
            "tasks_created": [],
            "tasks_listed": [],
            "tasks_changed": False,
        }
    if cmd == "/agenda":
        await status("Abriendo agenda…")
        agenda = await memory.list_agenda_upcoming(limit=20)
        if not agenda:
            reply = "Agenda vacía."
            listed: list[dict[str, Any]] = []
        else:
            lines = [f"- {starts} — {title}" for _i, starts, title, _st in agenda]
            reply = "Agenda:\n" + "\n".join(lines)
            listed = []
        await _persist_exchange(memory, text, reply)
        return {
            "reply": reply,
            "tasks_created": [],
            "tasks_listed": listed,
            "tasks_changed": False,
        }
    if cmd == "/diario":
        await status("Leyendo diario…")
        day = session_date_str()
        entries = await memory.list_diary_for_day(day)
        if not entries:
            reply = f"Diario vacío para {day}."
        else:
            lines = [f"- {entry}" for _id, entry in entries]
            reply = f"Diario {day}:\n" + "\n".join(lines)
        await _persist_exchange(memory, text, reply)
        return {
            "reply": reply,
            "tasks_created": [],
            "tasks_listed": [],
            "tasks_changed": False,
        }

    llm = getattr(request.app.state, "llm", None)
    if llm is None:
        raise HTTPException(status_code=503, detail="llm not ready")

    before = {t.id for t in await memory.list_tasks(status="open", limit=100)}
    reply = await llm.ask(text, on_status=on_status)
    after_rows = await memory.list_tasks(status="open", limit=100)
    after = {t.id for t in after_rows}
    created = [_task_dict(t) for t in after_rows if t.id in (after - before)]

    listed = list(created)
    id_re = re.compile(r"(?:tarea|task|id)\s*#?\s*(\d+)|\b(\d+)\.\s+\S", re.I)
    seen = {t["id"] for t in listed}
    for m in id_re.finditer(reply or ""):
        for g in m.groups():
            if not g:
                continue
            tid = int(g)
            if tid in seen:
                continue
            row = await memory.get_task(tid)
            if row is not None:
                listed.append(_task_dict(row))
                seen.add(tid)

    return {
        "reply": reply,
        "tasks_created": created,
        "tasks_listed": listed,
        "tasks_changed": bool(created) or before != after,
    }


@router.post("/chat", dependencies=[Depends(require_console_auth)])
async def chat(request: Request, body: ChatBody) -> dict[str, Any]:
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="empty text")
    return await _run_chat(request, text)


@router.post("/chat/stream", dependencies=[Depends(require_console_auth)])
async def chat_stream(request: Request, body: ChatBody) -> StreamingResponse:
    """SSE: status lines while working, then a final `done` event with the reply."""
    import asyncio
    import json

    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="empty text")

    queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()

    async def on_status(msg: str) -> None:
        await queue.put({"type": "status", "text": msg})

    async def worker() -> None:
        try:
            result = await _run_chat(request, text, on_status=on_status)
            await queue.put({"type": "done", **result})
        except HTTPException as e:
            await queue.put(
                {"type": "error", "detail": e.detail, "status": e.status_code}
            )
        except Exception as e:
            await queue.put({"type": "error", "detail": str(e), "status": 500})
        finally:
            await queue.put(None)

    async def event_gen():
        task = asyncio.create_task(worker())
        try:
            while True:
                if await request.is_disconnected():
                    break
                item = await queue.get()
                if item is None:
                    break
                yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"
        finally:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
