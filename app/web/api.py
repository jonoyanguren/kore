"""HTTP API for the web console: auth + tasks + chat."""

from __future__ import annotations

import io
import re
import zipfile
from typing import Annotated, Any, Literal

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.config import settings
from app.kernel.briefing import build_day_briefing
from app.llm.openrouter_credits import fetch_usage
from app.llm.transcribe import MAX_AUDIO_BYTES, transcribe_audio
from app.storage.memory import TaskRow, VALID_TASK_STATUSES, format_tasks_message
from app.storage.task_tools import purge_done_tasks_archiving, sync_tasks_vault
from app.timeutil import (
    format_madrid_clock,
    format_relative_es,
    now_madrid,
    session_date_str,
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


@router.get("/usage", dependencies=[Depends(require_console_auth)])
async def usage(force: bool = False) -> dict[str, Any]:
    """OpenRouter spend: usage_usd, total_usd, pct_used (cached ~60s)."""
    snap = await fetch_usage(force=force)
    if snap is None:
        return {"ok": False, "usage": None}
    return {"ok": True, "usage": snap.as_dict()}


class MemoryBody(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    category: str = Field(default="general", max_length=64)


class DiaryBody(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    day: str | None = None


@router.get("/memory/categories", dependencies=[Depends(require_console_auth)])
async def memory_categories(request: Request) -> dict[str, list[str]]:
    cats = await request.app.state.memory.list_categories()
    return {"categories": cats}


@router.get("/memory", dependencies=[Depends(require_console_auth)])
async def list_memory(
    request: Request,
    category: str | None = None,
    limit: int = 40,
) -> dict[str, Any]:
    rows = await request.app.state.memory.list_memory(
        category=category, limit=min(max(limit, 1), 100)
    )
    return {
        "items": [
            {"id": i, "category": cat, "text": text} for i, cat, text in rows
        ]
    }


@router.post("/memory", dependencies=[Depends(require_console_auth)])
async def create_memory(request: Request, body: MemoryBody) -> dict[str, Any]:
    cat = (body.category or "general").strip().lower() or "general"
    item_id = await request.app.state.memory.save_memory(
        category=cat, text=body.text, source="console"
    )
    vault = request.app.state.vault
    vault.append_memory(cat, item_id, body.text)
    return {"item": {"id": item_id, "category": cat, "text": body.text.strip()}}


@router.delete("/memory/{item_id}", dependencies=[Depends(require_console_auth)])
async def delete_memory_item(request: Request, item_id: int) -> dict[str, bool]:
    memory = request.app.state.memory
    existing = await memory.get_memory(item_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="memory not found")
    _id, cat, _text = existing
    ok = await memory.delete_memory(item_id)
    if not ok:
        raise HTTPException(status_code=404, detail="memory not found")
    items = await memory.list_memory_all_by_category(cat)
    request.app.state.vault.rewrite_memory_category(cat, items)
    return {"ok": True}


@router.delete(
    "/memory/category/{category}",
    dependencies=[Depends(require_console_auth)],
)
async def delete_memory_category(request: Request, category: str) -> dict[str, Any]:
    cat = category.strip().lower()
    if not cat or len(cat) > 64:
        raise HTTPException(status_code=400, detail="invalid category")
    deleted = await request.app.state.memory.delete_memory_category(cat)
    request.app.state.vault.rewrite_memory_category(cat, [])
    return {"ok": True, "category": cat, "deleted": deleted}


@router.get("/privacy/overview", dependencies=[Depends(require_console_auth)])
async def privacy_overview(request: Request) -> dict[str, Any]:
    memory = request.app.state.memory
    counts = await memory.memory_category_counts()
    diary_today = await memory.list_diary_for_day(session_date_str())
    open_tasks = await memory.list_tasks(status="open", limit=100)
    return {
        "memory_categories": [
            {"category": cat, "count": n} for cat, n in counts
        ],
        "memory_total": sum(n for _c, n in counts),
        "diary_today": len(diary_today),
        "tasks_open": len(open_tasks),
        "vault_root": str(request.app.state.vault.root),
    }


@router.get("/vault/export", dependencies=[Depends(require_console_auth)])
async def vault_export(request: Request) -> StreamingResponse:
    """Zip of markdown vault (memory/diary/agenda/dreams/tasks)."""
    root = request.app.state.vault.root
    request.app.state.vault.ensure()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            zf.write(path, arcname=str(path.relative_to(root)))
    buf.seek(0)
    day = session_date_str()
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="kore-vault-{day}.zip"',
        },
    )


@router.post("/transcribe", dependencies=[Depends(require_console_auth)])
async def transcribe(
    file: UploadFile = File(...),
) -> dict[str, str]:
    """Mic blob → text (OpenRouter Whisper). Does not send to chat."""
    data = await file.read()
    if len(data) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="audio too large")
    try:
        text = await transcribe_audio(data, mime=file.content_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=502, detail=f"transcription failed: {e}"
        ) from e
    return {"text": text}


@router.get("/diary", dependencies=[Depends(require_console_auth)])
async def list_diary(
    request: Request,
    day: str | None = None,
) -> dict[str, Any]:
    day = day or session_date_str()
    rows = await request.app.state.memory.list_diary_for_day(day)
    return {
        "day": day,
        "entries": [{"id": i, "text": text} for i, text in rows],
    }


@router.post("/diary", dependencies=[Depends(require_console_auth)])
async def create_diary(request: Request, body: DiaryBody) -> dict[str, Any]:
    day = body.day or session_date_str()
    entry_id = await request.app.state.memory.add_diary_entry(
        text=body.text, day=day, source="console"
    )
    request.app.state.vault.append_diary(day, entry_id, body.text)
    return {"entry": {"id": entry_id, "text": body.text.strip(), "day": day}}


@router.delete("/diary/{entry_id}", dependencies=[Depends(require_console_auth)])
async def delete_diary(request: Request, entry_id: int) -> dict[str, bool]:
    memory = request.app.state.memory
    day = await memory.delete_diary_entry(entry_id)
    if day is None:
        raise HTTPException(status_code=404, detail="diary entry not found")
    entries = await memory.list_diary_for_day(day)
    request.app.state.vault.rewrite_diary_day(day, entries)
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


@router.delete("/tasks/completed", dependencies=[Depends(require_console_auth)])
async def purge_completed_tasks(request: Request) -> dict[str, Any]:
    """Archive done tasks to vault/tasks/done.md, then hard-delete from DB."""
    deleted = await purge_done_tasks_archiving(
        request.app.state.memory,
        request.app.state.vault,
    )
    return {"ok": True, "deleted": deleted, "archived": deleted > 0}


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


@router.get("/day", dependencies=[Depends(require_console_auth)])
async def day_snapshot(request: Request) -> dict[str, Any]:
    """Day strip: clock, counts, structured briefing (tasks / meetings / help)."""
    memory = request.app.state.memory
    vault = request.app.state.vault
    today = session_date_str()
    clock = format_madrid_clock()
    weekday = clock.split(",")[0]

    open_tasks = await memory.list_tasks(status="open", limit=100)
    n_progress = sum(1 for t in open_tasks if t.status == "in_progress")
    n_pending = sum(1 for t in open_tasks if t.status == "open")

    briefing = await build_day_briefing(memory, vault)

    return {
        "today": today,
        "clock": clock,
        "headline": weekday,
        "greeting": f"Hola, {settings.owner_name}",
        "owner_name": settings.owner_name,
        "tasks": {"in_progress": n_progress, "open": n_pending},
        "agenda": briefing["meetings"],
        "briefing": briefing,
        "dream": (
            {
                "day": briefing["day"],
                "excerpt": (briefing["help"][0] if briefing["help"] else None),
            }
            if briefing["has_dream"]
            else None
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

    # Explicit task refs only (not "12. title" list format — floods the UI).
    task_ids: set[int] = set()
    id_re = re.compile(
        r"(?:tarea|task)\s*#?\s*(\d+)|\bid\s*#?\s*(\d+)\b",
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
    ask_text = text

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
    reply = await llm.ask(
        ask_text,
        on_status=on_status,
        persist_user_text=text if ask_text != text else None,
    )
    after_rows = await memory.list_tasks(status="open", limit=100)
    after = {t.id for t in after_rows}
    created = [_task_dict(t) for t in after_rows if t.id in (after - before)]
    # Only attach cards for tasks created this turn — do NOT scrape numbered
    # lists from the reply (list_tasks format "12. title" was flooding the UI).
    return {
        "reply": reply,
        "tasks_created": created,
        "tasks_listed": list(created),
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
            result = await _run_chat(
                request, text, on_status=on_status
            )
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
