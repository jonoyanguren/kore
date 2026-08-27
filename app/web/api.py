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
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from pydantic import BaseModel, Field

from app.config import settings
from app.integrations.gmail.client import (
    GmailApiError,
    GmailConfigError,
    GmailNotConnectedError,
)
from app.integrations.gmail.oauth import (
    build_authorize_url,
    consume_oauth_state,
    create_oauth_state,
    exchange_code,
)
from app.integrations.gmail.to_task import create_task_from_email
from app.integrations.gmail.reply import draft_reply, send_reply
from app.integrations.google_calendar.actions import (
    create_task_from_event,
    prep_for_event,
)
from app.integrations.google_calendar.client import meeting_dict_from_event
from app.integrations.google_calendar.propose_stash import (
    clear_calendar_stash,
    take_calendar_created,
    take_calendar_deleted,
)
from app.integrations.gmail.triage_log import (
    list_marked_read,
    marked_read_path_for_db,
    today_madrid_start_unix,
)
from app.kernel.briefing import build_day_briefing
from app.kernel.mission_clarify import clarify_mission
from app.kernel.mission_plan import MissionPlan
from app.storage.tools import format_memory_excerpt
from app.llm.mission_quality import (
    mission_mode_options,
    mode_label,
    normalize_mode,
    resolve_mission_model,
)
from app.llm.openrouter_credits import fetch_usage
from app.llm.llm_routing import llm_routing
from app.llm.transcribe import MAX_AUDIO_BYTES, transcribe_audio
from app.storage.memory import TaskRow, VALID_TASK_STATUSES, format_tasks_message, MissionRow
from app.storage.task_tools import purge_done_tasks_archiving, sync_tasks_vault
from app.timeutil import (
    format_madrid_clock,
    format_relative_es,
    now_madrid,
    session_date_str,
)
from app.web.auth import (
    COOKIE_NAME,
    SESSION_MAX_AGE,
    accounts_of,
    bind_home,
    console_secret_configured,
    require_console_auth,
)
from app.web.auth import _secrets_match

router = APIRouter(prefix="/api", tags=["console"])

TaskStatus = Literal["open", "in_progress", "done", "cancelled"]


def _memory(request: Request):
    bound = getattr(request.state, "memory", None)
    if bound is not None:
        return bound
    return request.app.state.memory


def _vault(request: Request):
    bound = getattr(request.state, "vault", None)
    if bound is not None:
        return bound
    return request.app.state.vault


def _cookie_secure(request: Request) -> bool:
    return request.url.scheme == "https"


def _set_session_cookie(response: Response, token: str, request: Request) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=_cookie_secure(request),
        max_age=SESSION_MAX_AGE,
        path="/",
    )


def _clear_session_cookie(response: Response, request: Request) -> None:
    # Must match set_cookie flags or the browser keeps the cookie (HTTPS Fly).
    response.delete_cookie(
        COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="lax",
        secure=_cookie_secure(request),
    )


class LoginBody(BaseModel):
    secret: str = ""
    email: str = ""
    password: str = ""


class RegisterBody(BaseModel):
    email: str = Field(min_length=3, max_length=200)
    password: str = Field(min_length=8, max_length=200)
    owner_name: str = Field(default="", max_length=80)


class CompanionBody(BaseModel):
    owner_name: str = Field(default="", max_length=80)
    companion_name: str = Field(min_length=1, max_length=80)
    companion_tone: str = Field(min_length=1, max_length=8000)


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


@router.post("/register")
async def register(
    body: RegisterBody, request: Request, response: Response
) -> dict[str, Any]:
    accounts = accounts_of(request)
    if accounts is None:
        raise HTTPException(status_code=503, detail="accounts not ready")
    try:
        user = await accounts.create_user(
            email=body.email,
            password=body.password,
            owner_name=body.owner_name.strip() or body.email.split("@")[0],
            onboarded=False,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    homes = getattr(request.app.state, "homes", None)
    if homes is not None:
        await homes.open(user.id)
    token = await accounts.create_session(user.id)
    _set_session_cookie(response, token, request)
    await bind_home(request, user)
    return {"ok": True, "user": _user_public(user)}


@router.post("/login")
async def login(body: LoginBody, request: Request, response: Response) -> dict[str, Any]:
    accounts = accounts_of(request)
    email = (body.email or "").strip()
    password = body.password or ""
    secret = (body.secret or "").strip()

    if email and password and accounts is not None:
        user = await accounts.authenticate(email, password)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized"
            )
        token = await accounts.create_session(user.id)
        _set_session_cookie(response, token, request)
        return {"ok": True, "user": _user_public(user)}

    expected = console_secret_configured()
    if not _secrets_match(secret, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized"
        )
    if accounts is not None:
        user = await accounts.legacy_user()
        if user is not None:
            token = await accounts.create_session(user.id)
            _set_session_cookie(response, token, request)
            return {"ok": True, "user": _user_public(user)}
    _set_session_cookie(response, secret, request)
    return {"ok": True}


@router.post("/logout")
async def logout(request: Request, response: Response) -> dict[str, bool]:
    token = request.cookies.get(COOKIE_NAME)
    accounts = accounts_of(request)
    if token and accounts is not None:
        await accounts.delete_session(token)
    _clear_session_cookie(response, request)
    return {"ok": True}


def _user_public(user) -> dict[str, Any]:
    return {
        "id": user.id,
        "email": user.email,
        "owner_name": user.owner_name,
        "companion_name": user.companion_name,
        "companion_tone": user.companion_tone,
        "onboarded": user.onboarded,
        "legacy": user.legacy_prompts,
    }


@router.get("/me", dependencies=[Depends(require_console_auth)])
async def me(request: Request) -> dict[str, Any]:
    user = getattr(request.state, "user", None)
    if user is not None:
        return {"ok": True, "user": _user_public(user)}
    return {"ok": True, "user": None}


@router.put("/me/companion", dependencies=[Depends(require_console_auth)])
async def update_companion(request: Request, body: CompanionBody) -> dict[str, Any]:
    user = getattr(request.state, "user", None)
    accounts = accounts_of(request)
    if user is None or accounts is None:
        raise HTTPException(status_code=401, detail="unauthorized")
    name = body.companion_name.strip()
    tone = body.companion_tone.strip()
    if not name or not tone:
        raise HTTPException(status_code=400, detail="nombre y tono obligatorios")
    updated = await accounts.update_companion(
        user.id,
        owner_name=body.owner_name.strip() or user.owner_name,
        companion_name=name,
        companion_tone=tone,
        onboarded=True,
    )
    assert updated is not None
    await bind_home(request, updated)
    return {"ok": True, "user": _user_public(updated)}


@router.get("/usage", dependencies=[Depends(require_console_auth)])
async def usage(force: bool = False) -> dict[str, Any]:
    """OpenRouter spend: usage_usd, total_usd, pct_used (cached ~60s)."""
    snap = await fetch_usage(force=force)
    if snap is None:
        return {"ok": False, "usage": None}
    return {"ok": True, "usage": snap.as_dict()}


@router.get("/spend", dependencies=[Depends(require_console_auth)])
async def spend_ledger(
    request: Request,
    days: int = Query(7, ge=1, le=90),
    limit: int = Query(80, ge=1, le=300),
) -> dict[str, Any]:
    """Local LLM spend ledger: events + totals for the last N Madrid days."""
    from datetime import timedelta

    from app.timeutil import now_madrid, session_date_str

    today = session_date_str()
    start = (now_madrid().date() - timedelta(days=days - 1)).isoformat()
    memory = _memory(request)
    summary = await memory.summarize_llm_spend(day_from=start, day_to=today)
    events = await memory.list_llm_spend(day_from=start, day_to=today, limit=limit)
    today_usd = next(
        (d["usd"] for d in summary["by_day"] if d["day"] == today),
        0.0,
    )
    return {
        "ok": True,
        "day_from": start,
        "day_to": today,
        "today_usd": today_usd,
        "summary": summary,
        "events": events,
    }


@router.get("/llm-routing", dependencies=[Depends(require_console_auth)])
async def llm_routing_endpoint() -> dict[str, Any]:
    """Daily/strong models + approx prices for the Más drawer."""
    return {"ok": True, **llm_routing()}


class MemoryBody(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    category: str = Field(default="general", max_length=64)


class DiaryBody(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    day: str | None = None


@router.get("/memory/categories", dependencies=[Depends(require_console_auth)])
async def memory_categories(request: Request) -> dict[str, list[str]]:
    cats = await _memory(request).list_categories()
    return {"categories": cats}


@router.get("/memory", dependencies=[Depends(require_console_auth)])
async def list_memory(
    request: Request,
    category: str | None = None,
    limit: int = 40,
) -> dict[str, Any]:
    rows = await _memory(request).list_memory(
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
    item_id = await _memory(request).save_memory(
        category=cat, text=body.text, source="console"
    )
    vault = _vault(request)
    vault.append_memory(cat, item_id, body.text)
    return {"item": {"id": item_id, "category": cat, "text": body.text.strip()}}


@router.delete("/memory/{item_id}", dependencies=[Depends(require_console_auth)])
async def delete_memory_item(request: Request, item_id: int) -> dict[str, bool]:
    memory = _memory(request)
    existing = await memory.get_memory(item_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="memory not found")
    _id, cat, _text = existing
    ok = await memory.delete_memory(item_id)
    if not ok:
        raise HTTPException(status_code=404, detail="memory not found")
    items = await memory.list_memory_all_by_category(cat)
    _vault(request).rewrite_memory_category(cat, items)
    return {"ok": True}


@router.delete(
    "/memory/category/{category}",
    dependencies=[Depends(require_console_auth)],
)
async def delete_memory_category(request: Request, category: str) -> dict[str, Any]:
    cat = category.strip().lower()
    if not cat or len(cat) > 64:
        raise HTTPException(status_code=400, detail="invalid category")
    deleted = await _memory(request).delete_memory_category(cat)
    _vault(request).rewrite_memory_category(cat, [])
    return {"ok": True, "category": cat, "deleted": deleted}


@router.get("/privacy/overview", dependencies=[Depends(require_console_auth)])
async def privacy_overview(request: Request) -> dict[str, Any]:
    memory = _memory(request)
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
        "vault_root": str(_vault(request).root),
    }


@router.get("/vault/export", dependencies=[Depends(require_console_auth)])
async def vault_export(request: Request) -> StreamingResponse:
    """Zip of markdown vault (memory/diary/agenda/dreams/tasks)."""
    root = _vault(request).root
    _vault(request).ensure()
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
    rows = await _memory(request).list_diary_for_day(day)
    return {
        "day": day,
        "entries": [{"id": i, "text": text} for i, text in rows],
    }


@router.post("/diary", dependencies=[Depends(require_console_auth)])
async def create_diary(request: Request, body: DiaryBody) -> dict[str, Any]:
    day = body.day or session_date_str()
    entry_id = await _memory(request).add_diary_entry(
        text=body.text, day=day, source="console"
    )
    _vault(request).append_diary(day, entry_id, body.text)
    return {"entry": {"id": entry_id, "text": body.text.strip(), "day": day}}


@router.delete("/diary/{entry_id}", dependencies=[Depends(require_console_auth)])
async def delete_diary(request: Request, entry_id: int) -> dict[str, bool]:
    memory = _memory(request)
    day = await memory.delete_diary_entry(entry_id)
    if day is None:
        raise HTTPException(status_code=404, detail="diary entry not found")
    entries = await memory.list_diary_for_day(day)
    _vault(request).rewrite_diary_day(day, entries)
    return {"ok": True}


@router.get("/tasks", dependencies=[Depends(require_console_auth)])
async def list_tasks(
    request: Request,
    status_filter: Annotated[str, Query(alias="status")] = "open",
    project: str | None = None,
    limit: int = 50,
) -> dict[str, list[dict[str, Any]]]:
    rows = await _memory(request).list_tasks(
        status=status_filter,
        limit=min(limit, 100),
        project=project,
    )
    return {"tasks": [_task_dict(r) for r in rows]}


@router.post("/tasks", dependencies=[Depends(require_console_auth)])
async def create_task(request: Request, body: CreateTaskBody) -> dict[str, Any]:
    if body.status not in VALID_TASK_STATUSES:
        raise HTTPException(status_code=400, detail="invalid status")
    task_id = await _memory(request).add_task(
        title=body.title,
        due_at=body.due_at,
        priority=body.priority,
        notes=body.notes,
        url=body.url,
        project=body.project,
        status=body.status,
    )
    await sync_tasks_vault(_memory(request), _vault(request))
    task = await _memory(request).get_task(task_id)
    assert task is not None
    return {"task": _task_dict(task)}


@router.patch("/tasks/{task_id}", dependencies=[Depends(require_console_auth)])
async def patch_task(
    request: Request, task_id: int, body: PatchTaskBody
) -> dict[str, Any]:
    ok = await _memory(request).update_task(
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
    await sync_tasks_vault(_memory(request), _vault(request))
    task = await _memory(request).get_task(task_id)
    assert task is not None
    return {"task": _task_dict(task)}


@router.delete("/tasks/completed", dependencies=[Depends(require_console_auth)])
async def purge_completed_tasks(request: Request) -> dict[str, Any]:
    """Archive done tasks to vault/tasks/done.md, then hard-delete from DB."""
    deleted = await purge_done_tasks_archiving(
        _memory(request),
        _vault(request),
    )
    return {"ok": True, "deleted": deleted, "archived": deleted > 0}


@router.post("/tasks/{task_id}/complete", dependencies=[Depends(require_console_auth)])
async def complete_task(request: Request, task_id: int) -> dict[str, Any]:
    ok = await _memory(request).complete_task(task_id)
    if not ok:
        raise HTTPException(status_code=404, detail="task not found")
    await sync_tasks_vault(_memory(request), _vault(request))
    task = await _memory(request).get_task(task_id)
    assert task is not None
    return {"task": _task_dict(task)}


@router.delete("/tasks/{task_id}", dependencies=[Depends(require_console_auth)])
async def delete_task(request: Request, task_id: int) -> dict[str, Any]:
    ok = await _memory(request).delete_task(task_id)
    if not ok:
        raise HTTPException(status_code=404, detail="task not found")
    await sync_tasks_vault(_memory(request), _vault(request))
    return {"ok": True}


# --- Missions (Phase 3) ------------------------------------------------------


class CreateMissionBody(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    brief: str = Field(default="", max_length=8000)
    launch: bool = True
    tick_seconds: int = Field(default=10, ge=5, le=3600)
    quality: str = Field(default="normal", max_length=20)
    mode: str | None = Field(default=None, max_length=20)

    def resolved_mode(self) -> str:
        return normalize_mode(self.mode or self.quality)


class ClarifyHistoryItem(BaseModel):
    question: str = Field(default="", max_length=500)
    answer: str = Field(default="", max_length=2000)


class ClarifyMissionBody(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    brief: str = Field(default="", max_length=8000)
    history: list[ClarifyHistoryItem] = Field(default_factory=list)
    round: int = Field(default=1, ge=1, le=2)
    quality: str = Field(default="normal", max_length=20)
    mode: str | None = Field(default=None, max_length=20)

    def resolved_mode(self) -> str:
        return normalize_mode(self.mode or self.quality)


def _mission_dict(row: MissionRow, *, markdown: str | None = None) -> dict[str, Any]:
    plan = MissionPlan.from_json(row.plan_json)
    plan_out: dict[str, Any] | None = None
    if plan is not None:
        plan_out = {
            "tasks": [
                {
                    "title": t.title,
                    "goal": t.goal,
                    "status": t.status,
                }
                for t in plan.tasks
            ],
            "handoff": plan.handoff or None,
            "completed": plan.completed_count(),
            "total": len(plan.tasks),
        }
        if plan.cost and (plan.cost.usd > 0 or plan.cost.llm_calls > 0):
            plan_out["cost"] = plan.cost.to_dict()
    mode = normalize_mode(row.quality)
    out: dict[str, Any] = {
        "id": row.id,
        "title": row.title,
        "status": row.status,
        "brief": row.brief,
        "quality": mode,
        "mode": mode,
        "mode_label": mode_label(mode),
        "model": resolve_mission_model(mode),
        "step_index": row.step_index,
        "max_ticks": row.max_ticks,
        "tick_seconds": row.tick_seconds,
        "next_run_at": row.next_run_at,
        "result_path": row.result_path,
        "error": row.error,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "plan": plan_out,
    }
    if markdown is not None:
        out["markdown"] = markdown
    return out


@router.get("/missions/quality-options", dependencies=[Depends(require_console_auth)])
async def missions_quality_options() -> dict[str, Any]:
    opts = mission_mode_options()
    return {"ok": True, "options": opts}


@router.get("/missions/mode-options", dependencies=[Depends(require_console_auth)])
async def missions_mode_options() -> dict[str, Any]:
    return {"ok": True, "options": mission_mode_options()}


@router.get("/missions", dependencies=[Depends(require_console_auth)])
async def list_missions(
    request: Request,
    include_done: bool = Query(True),
) -> dict[str, Any]:
    rows = await _memory(request).list_missions(include_done=include_done)
    return {"missions": [_mission_dict(r) for r in rows]}


@router.post("/missions", dependencies=[Depends(require_console_auth)])
async def create_mission(request: Request, body: CreateMissionBody) -> dict[str, Any]:
    memory = _memory(request)
    vault = _vault(request)
    status_v = "queued" if body.launch else "draft"
    next_run = now_madrid().replace(microsecond=0).isoformat() if body.launch else None
    quality = body.resolved_mode()
    mid = await memory.add_mission(
        body.title.strip(),
        brief=body.brief.strip(),
        quality=quality,
        status=status_v,
        max_ticks=1,
        tick_seconds=body.tick_seconds,
        next_run_at=next_run,
    )
    model = resolve_mission_model(quality)
    path = vault.write_mission(
        mid,
        f"# {body.title.strip()}\n\n"
        f"> Estado: {'en cola · planificando…' if body.launch else 'borrador'}\n"
        f"> Modo: {mode_label(quality)} · `{model}`\n\n"
        f"## Encargo\n\n{body.brief.strip() or '(sin brief)'}\n",
    )
    rel = str(path.relative_to(vault.root)) if path.is_relative_to(vault.root) else str(path)
    row = await memory.update_mission(mid, result_path=rel)
    assert row is not None
    await memory.add_mission_event(
        mid, "created", f"{'launch' if body.launch else 'draft'}:{quality}"
    )
    return {"mission": _mission_dict(row)}


@router.post("/missions/clarify", dependencies=[Depends(require_console_auth)])
async def clarify_mission_endpoint(
    request: Request, body: ClarifyMissionBody
) -> dict[str, Any]:
    """Intake questions (or mark ready) before creating a mission."""
    llm = request.app.state.llm_client
    hist = [
        {"question": h.question.strip(), "answer": h.answer.strip()}
        for h in body.history
    ]
    result = await clarify_mission(
        llm,
        title=body.title.strip(),
        brief=body.brief.strip(),
        history=hist,
        round_n=body.round,
        quality=body.resolved_mode(),
        memory_excerpt=await format_memory_excerpt(_memory(request)),
    )
    return {
        "ok": True,
        "ready": result.ready,
        "questions": result.questions,
        "refined_brief": result.refined_brief,
        "round": result.round,
        "rounds_left": result.rounds_left,
    }


@router.get("/missions/{mission_id}", dependencies=[Depends(require_console_auth)])
async def get_mission(request: Request, mission_id: int) -> dict[str, Any]:
    row = await _memory(request).get_mission(mission_id)
    if row is None:
        raise HTTPException(status_code=404, detail="mission not found")
    md = _vault(request).read_mission(mission_id)
    return {"mission": _mission_dict(row, markdown=md or "")}


@router.post(
    "/missions/{mission_id}/cancel",
    dependencies=[Depends(require_console_auth)],
)
async def cancel_mission(request: Request, mission_id: int) -> dict[str, Any]:
    row = await _memory(request).get_mission(mission_id)
    if row is None:
        raise HTTPException(status_code=404, detail="mission not found")
    if row.status in ("done", "failed", "cancelled"):
        return {"mission": _mission_dict(row)}
    updated = await _memory(request).update_mission(
        mission_id,
        status="cancelled",
        clear_next_run=True,
    )
    await _memory(request).add_mission_event(mission_id, "cancelled", None)
    assert updated is not None
    return {"mission": _mission_dict(updated)}


@router.post(
    "/missions/{mission_id}/relaunch",
    dependencies=[Depends(require_console_auth)],
)
async def relaunch_mission(request: Request, mission_id: int) -> dict[str, Any]:
    """Reset a mission and queue it again (useful after stub → real research)."""
    row = await _memory(request).get_mission(mission_id)
    if row is None:
        raise HTTPException(status_code=404, detail="mission not found")
    next_run = now_madrid().replace(microsecond=0).isoformat()
    updated = await _memory(request).update_mission(
        mission_id,
        status="queued",
        step_index=0,
        max_ticks=1,
        plan_json="",
        next_run_at=next_run,
        clear_error=True,
    )
    assert updated is not None
    _vault(request).write_mission(
        mission_id,
        f"# {updated.title}\n\n"
        f"> Estado: en cola (relanzada) · planificando…\n\n"
        f"## Encargo\n\n{updated.brief.strip() or '(sin brief)'}\n",
    )
    await _memory(request).add_mission_event(mission_id, "relaunch", None)
    return {"mission": _mission_dict(updated)}


class ChatBody(BaseModel):
    text: str = Field(min_length=1, max_length=8000)


@router.get("/day", dependencies=[Depends(require_console_auth)])
async def day_snapshot(request: Request) -> dict[str, Any]:
    """Day strip: clock, counts, structured briefing (tasks / meetings / help)."""
    memory = _memory(request)
    vault = _vault(request)
    user = getattr(request.state, "user", None)
    owner = (user.owner_name if user is not None else "") or settings.owner_name
    today = session_date_str()
    clock = format_madrid_clock()
    weekday = clock.split(",")[0]

    open_tasks = await memory.list_tasks(status="open", limit=100)
    n_progress = sum(1 for t in open_tasks if t.status == "in_progress")
    n_pending = sum(1 for t in open_tasks if t.status == "open")

    google_meetings: list[dict[str, Any]] = []
    calendar_meta: dict[str, Any] = {
        "ready": False,
        "error": None,
        "error_code": None,
    }
    calendar = getattr(request.app.state, "calendar", None)
    gmail_for_cal = getattr(request.app.state, "gmail", None)
    if calendar is not None and gmail_for_cal is not None:
        st_cal = gmail_for_cal.status()
        calendar_meta["ready"] = bool(st_cal.get("calendar_ready"))
        if st_cal.get("connected") and not st_cal.get("calendar_ready"):
            calendar_meta["error_code"] = "needs_reconnect"
            calendar_meta["error"] = (
                "Falta permiso de Calendar. Reconecta Google en Más → Gmail."
            )
        elif st_cal.get("calendar_ready"):
            try:
                from datetime import datetime, timedelta
                from zoneinfo import ZoneInfo

                from app.integrations.google_calendar.client import (
                    meeting_dict_from_event,
                )
                from app.timeutil import today_madrid

                madrid = ZoneInfo("Europe/Madrid")
                start = datetime.combine(
                    today_madrid(), datetime.min.time(), tzinfo=madrid
                )
                end = start + timedelta(days=4)
                events = await calendar.list_events(
                    time_min=start, time_max=end, max_total=20
                )
                google_meetings = [meeting_dict_from_event(e) for e in events]
            except GmailApiError as exc:
                calendar_meta["error_code"] = exc.code
                calendar_meta["error"] = exc.message
            except Exception:
                calendar_meta["error_code"] = "api"
                calendar_meta["error"] = "No se pudo cargar Google Calendar."

    briefing = await build_day_briefing(
        memory, vault, google_meetings=google_meetings
    )

    inbox: dict[str, Any] = {
        "connected": False,
        "messages": [],
        "error": None,
        "error_code": None,
        "gmail_ready": False,
        "can_send": False,
        "marked_read_today": [],
    }
    gmail = getattr(request.app.state, "gmail", None)
    if gmail is not None:
        st = gmail.status()
        inbox["connected"] = bool(st.get("connected"))
        inbox["email"] = st.get("email") or ""
        inbox["gmail_ready"] = bool(st.get("gmail_ready"))
        inbox["can_send"] = bool(st.get("can_send"))
        if inbox["connected"] and not inbox["gmail_ready"]:
            inbox["error_code"] = "needs_reconnect"
            inbox["error"] = (
                "Falta permiso de Gmail. Desconecta y vuelve a conectar en Más → Gmail."
            )
        elif inbox["connected"]:
            try:
                msgs = await gmail.list_messages(
                    query="is:unread newer_than:2d", max_results=5
                )
                inbox["messages"] = [
                    {
                        "id": m.id,
                        "subject": m.subject,
                        "from": m.from_,
                        "snippet": m.snippet,
                        "date": m.date,
                        "permalink": m.permalink,
                    }
                    for m in msgs
                ]
            except GmailApiError as exc:
                inbox["error_code"] = exc.code
                inbox["error"] = exc.message
            except (GmailNotConnectedError, GmailConfigError) as exc:
                inbox["error_code"] = "auth"
                inbox["error"] = str(exc)
            except Exception:
                inbox["error_code"] = "api"
                inbox["error"] = (
                    "No se pudo cargar el correo. Revisa Más → Gmail."
                )
            inbox["marked_read_today"] = list_marked_read(
                marked_read_path_for_db(memory._db_path),
                limit=12,
                since=today_madrid_start_unix(),
            )

    return {
        "today": today,
        "clock": clock,
        "headline": weekday,
        "greeting": f"Hola, {owner}",
        "owner_name": owner,
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
        "inbox": inbox,
        "calendar": calendar_meta,
        "server_now": now_madrid().isoformat(),
    }


@router.get("/messages", dependencies=[Depends(require_console_auth)])
async def list_messages(
    request: Request,
    limit: int = 10,
    before: int | None = None,
) -> dict[str, Any]:
    page = min(max(limit, 1), 50)
    memory = _memory(request)
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

    def pack(
        *,
        reply: str,
        tasks_created: list[dict[str, Any]] | None = None,
        tasks_listed: list[dict[str, Any]] | None = None,
        tasks_changed: bool = False,
        calendar_created: dict[str, Any] | None = None,
        calendar_deleted: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "reply": reply,
            "tasks_created": tasks_created or [],
            "tasks_listed": tasks_listed if tasks_listed is not None else (tasks_created or []),
            "tasks_changed": tasks_changed,
            "calendar_created": calendar_created,
            "calendar_deleted": calendar_deleted,
        }

    memory = _memory(request)
    cmd = text.split()[0].lower() if text.startswith("/") else ""
    ask_text = text

    if cmd in ("/tareas", "/tasks"):
        await status("Listando tareas…")
        rows = await memory.list_tasks(status="open", limit=40)
        reply = format_tasks_message(rows, heading="Tareas")
        await _persist_exchange(memory, text, reply)
        return pack(reply=reply, tasks_listed=[_task_dict(t) for t in rows])
    if cmd == "/hora":
        await status("Mirando el reloj…")
        reply = format_madrid_clock()
        await _persist_exchange(memory, text, reply)
        return pack(reply=reply)
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
        return pack(reply=reply, tasks_listed=listed)
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
        return pack(reply=reply)
    if cmd in ("/dream", "/sueno", "/sueño"):
        await status("Generando dream…")
        vault = getattr(request.app.state, "vault", None)
        llm_client = getattr(request.app.state, "llm_client", None)
        if vault is None or llm_client is None:
            reply = "Sueño no disponible ahora."
            await _persist_exchange(memory, text, reply)
            return pack(reply=reply)
        parts = text.split(maxsplit=1)
        day_arg = parts[1].strip() if len(parts) > 1 else session_date_str()
        # Accept bare YYYY-MM-DD; otherwise default today (manual console path).
        if len(day_arg) >= 10 and day_arg[4] == "-" and day_arg[7] == "-":
            day_arg = day_arg[:10]
        else:
            day_arg = session_date_str()
        from app.kernel.dream import run_dream

        reply = await run_dream(
            memory,
            vault,
            llm_client,
            day=day_arg,
            telegram=None,
            notify=False,
            gmail=getattr(request.app.state, "gmail", None),
            calendar=getattr(request.app.state, "calendar", None),
        )
        await _persist_exchange(memory, text, reply)
        return pack(reply=reply)

    llm = getattr(request.app.state, "llm", None)
    if llm is None:
        raise HTTPException(status_code=503, detail="llm not ready")

    clear_calendar_stash()
    before = {t.id for t in await memory.list_tasks(status="open", limit=100)}
    reply = await llm.ask(
        ask_text,
        on_status=on_status,
        persist_user_text=text if ask_text != text else None,
    )
    after_rows = await memory.list_tasks(status="open", limit=100)
    after = {t.id for t in after_rows}
    created = [_task_dict(t) for t in after_rows if t.id in (after - before)]
    cal_created = take_calendar_created()
    cal_deleted = take_calendar_deleted()
    # Only attach cards for tasks created this turn — do NOT scrape numbered
    # lists from the reply (list_tasks format "12. title" was flooding the UI).
    return pack(
        reply=reply,
        tasks_created=created,
        tasks_listed=list(created),
        tasks_changed=bool(created) or before != after,
        calendar_created=cal_created,
        calendar_deleted=cal_deleted,
    )


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


# --- Gmail OAuth + inbox -------------------------------------------------


class CalendarEventActionBody(BaseModel):
    id: str | int | None = None
    title: str = ""
    starts_at: str = ""
    ends_at: str | None = None
    html_link: str | None = None
    calendar: str | None = None
    source: str | None = None
    all_day: bool | None = None


class CreateCalendarEventBody(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    starts_at: str = Field(min_length=10, max_length=32)
    ends_at: str = Field(min_length=10, max_length=32)
    description: str = Field(default="", max_length=8000)
    attendees: list[str] = Field(default_factory=list)


@router.post(
    "/calendar/events",
    dependencies=[Depends(require_console_auth)],
)
async def calendar_create_event(
    request: Request, body: CreateCalendarEventBody
) -> dict[str, Any]:
    """Create a timed event on Google Calendar primary (after chat confirm)."""
    calendar = getattr(request.app.state, "calendar", None)
    if calendar is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, detail="calendar_unavailable"
        )
    try:
        ev = await calendar.create_event(
            title=body.title.strip(),
            starts_at=body.starts_at.strip(),
            ends_at=body.ends_at.strip(),
            description=body.description.strip(),
            attendees=list(body.attendees or []),
        )
    except GmailNotConnectedError:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="google_not_connected"
        ) from None
    except GmailConfigError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from None
    except GmailApiError as exc:
        if exc.code == "needs_reconnect":
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail={"code": exc.code, "message": exc.message},
            ) from None
        if exc.code == "invalid":
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail={"code": exc.code, "message": exc.message},
            ) from None
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail={"code": exc.code, "message": exc.message},
        ) from None
    return {"ok": True, "event": meeting_dict_from_event(ev)}


@router.post(
    "/calendar/events/to-task",
    dependencies=[Depends(require_console_auth)],
)
async def calendar_event_to_task(
    request: Request, body: CalendarEventActionBody
) -> dict[str, Any]:
    """LLM proposes a local task from a calendar event."""
    llm = getattr(request.app.state, "llm_client", None)
    if llm is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="llm_unavailable")
    event = body.model_dump()
    result = await create_task_from_event(
        llm=llm,
        memory=_memory(request),
        vault=_vault(request),
        event=event,
    )
    if not result.get("ok"):
        err = str(result.get("error") or "failed")
        if err == "duplicate":
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail={"code": "duplicate", "message": result.get("detail")},
            )
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=err)
    return result


@router.post(
    "/calendar/events/prep",
    dependencies=[Depends(require_console_auth)],
)
async def calendar_event_prep(
    request: Request, body: CalendarEventActionBody
) -> dict[str, Any]:
    """Short pre-meeting brief from event + memory."""
    llm = getattr(request.app.state, "llm_client", None)
    if llm is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="llm_unavailable")
    result = await prep_for_event(
        llm=llm,
        memory=_memory(request),
        vault=_vault(request),
        event=body.model_dump(),
    )
    if not result.get("ok"):
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail=str(result.get("error") or "prep_failed"),
        )
    return result


@router.get("/gmail/status", dependencies=[Depends(require_console_auth)])
async def gmail_status(request: Request) -> dict[str, Any]:
    gmail = getattr(request.app.state, "gmail", None)
    if gmail is None:
        return {
            "configured": bool(
                settings.google_client_id.strip() and settings.google_client_secret.strip()
            ),
            "connected": False,
            "email": "",
            "scope": "gmail.modify",
            "gmail_ready": False,
        }
    return gmail.status()


@router.post(
    "/gmail/messages/{message_id}/to-task",
    dependencies=[Depends(require_console_auth)],
)
async def gmail_to_task(request: Request, message_id: str) -> dict[str, Any]:
    """LLM proposes a local task from a Gmail message (title/project/notes + link)."""
    gmail = getattr(request.app.state, "gmail", None)
    llm = getattr(request.app.state, "llm_client", None)
    if gmail is None or llm is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="gmail_unavailable")
    try:
        result = await create_task_from_email(
            gmail=gmail,
            llm=llm,
            memory=_memory(request),
            vault=_vault(request),
            message_id=message_id,
        )
    except GmailNotConnectedError:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="gmail_not_connected") from None
    except GmailConfigError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from None
    except GmailApiError as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail={"code": exc.code, "message": exc.message},
        ) from None
    if not result.get("ok"):
        err = str(result.get("error") or "failed")
        if err == "message_not_found":
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail=err)
        if err == "duplicate":
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail={"code": "duplicate", "message": result.get("detail")},
            )
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=err)
    return result


class GmailReplyBody(BaseModel):
    body: str = Field(min_length=1, max_length=20000)


@router.post(
    "/gmail/messages/{message_id}/reply-draft",
    dependencies=[Depends(require_console_auth)],
)
async def gmail_reply_draft(request: Request, message_id: str) -> dict[str, Any]:
    """LLM proposes an editable reply body for a Gmail message."""
    gmail = getattr(request.app.state, "gmail", None)
    llm = getattr(request.app.state, "llm_client", None)
    if gmail is None or llm is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="gmail_unavailable")
    st = gmail.status()
    if not st.get("can_send"):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail={
                "code": "needs_send_scope",
                "message": "Falta permiso de envío. Desconecta y reconecta Gmail en Más.",
            },
        )
    try:
        return await draft_reply(gmail=gmail, llm=llm, message_id=message_id)
    except LookupError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="message_not_found") from None
    except GmailNotConnectedError:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="gmail_not_connected") from None
    except GmailConfigError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from None
    except GmailApiError as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail={"code": exc.code, "message": exc.message},
        ) from None


@router.post(
    "/gmail/messages/{message_id}/reply",
    dependencies=[Depends(require_console_auth)],
)
async def gmail_reply_send(
    request: Request,
    message_id: str,
    payload: GmailReplyBody,
) -> dict[str, Any]:
    """Send a reply with the (edited) body. Requires gmail.send scope."""
    gmail = getattr(request.app.state, "gmail", None)
    if gmail is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="gmail_unavailable")
    st = gmail.status()
    if not st.get("can_send"):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail={
                "code": "needs_send_scope",
                "message": "Falta permiso de envío. Desconecta y reconecta Gmail en Más.",
            },
        )
    try:
        return await send_reply(gmail=gmail, message_id=message_id, body=payload.body)
    except LookupError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="message_not_found") from None
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None
    except GmailNotConnectedError:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="gmail_not_connected") from None
    except GmailConfigError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from None
    except GmailApiError as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail={"code": exc.code, "message": exc.message},
        ) from None


@router.get("/gmail/connect", dependencies=[Depends(require_console_auth)])
async def gmail_connect(request: Request) -> RedirectResponse:
    if not (
        settings.google_client_id.strip() and settings.google_client_secret.strip()
    ):
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gmail OAuth not configured (GOOGLE_CLIENT_ID/SECRET)",
        )
    user = getattr(request.state, "user", None)
    uid = int(user.id) if user is not None else None
    state = create_oauth_state(settings.storage_db_path, user_id=uid)
    url = build_authorize_url(
        client_id=settings.google_client_id,
        redirect_uri=settings.google_oauth_redirect_uri,
        state=state,
    )
    return RedirectResponse(url, status_code=status.HTTP_302_FOUND)


@router.get("/gmail/callback")
async def gmail_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> HTMLResponse:
    """Google redirects here (no console auth — CSRF via oauth state)."""
    if error:
        return _gmail_oauth_result_page(ok=False, detail=error)
    if not code or not state:
        return _gmail_oauth_result_page(ok=False, detail="missing_code_or_state")
    payload = consume_oauth_state(settings.storage_db_path, state)
    if not payload:
        return _gmail_oauth_result_page(ok=False, detail="invalid_or_expired_state")

    gmail = getattr(request.app.state, "gmail", None)
    http = getattr(request.app.state, "http", None)
    if gmail is None or http is None:
        return _gmail_oauth_result_page(ok=False, detail="gmail_client_unavailable")

    uid = payload.get("user_id")
    accounts = accounts_of(request)
    if uid is not None and accounts is not None:
        user = await accounts.get_user(int(uid))
        if user is not None:
            await bind_home(request, user)

    try:
        tokens = await exchange_code(
            http,
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            redirect_uri=settings.google_oauth_redirect_uri,
            code=code,
        )
        await gmail.save_tokens(tokens)
    except Exception as exc:
        return _gmail_oauth_result_page(ok=False, detail=str(exc))

    email = tokens.email or "Gmail"
    return _gmail_oauth_result_page(ok=True, detail=email)


@router.post("/gmail/disconnect", dependencies=[Depends(require_console_auth)])
async def gmail_disconnect(request: Request) -> dict[str, Any]:
    gmail = getattr(request.app.state, "gmail", None)
    if gmail is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="gmail_unavailable")
    gmail.disconnect()
    return {"ok": True}


@router.get("/gmail/inbox", dependencies=[Depends(require_console_auth)])
async def gmail_inbox(
    request: Request,
    q: str = Query("is:unread newer_than:1d"),
    limit: int = Query(15, ge=1, le=50),
) -> dict[str, Any]:
    gmail = getattr(request.app.state, "gmail", None)
    if gmail is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="gmail_unavailable")
    try:
        messages = await gmail.list_messages(query=q, max_results=limit)
    except GmailNotConnectedError:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="gmail_not_connected") from None
    except GmailConfigError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from None
    except GmailApiError as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail={"code": exc.code, "message": exc.message},
        ) from None
    except Exception:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail={"code": "api", "message": "Gmail no respondió bien ahora."},
        ) from None
    return {
        "query": q,
        "messages": [
            {
                "id": m.id,
                "subject": m.subject,
                "from": m.from_,
                "snippet": m.snippet,
                "date": m.date,
                "unread": m.unread,
                "permalink": m.permalink,
            }
            for m in messages
        ],
    }


@router.get("/gmail/marked-read", dependencies=[Depends(require_console_auth)])
async def gmail_marked_read(
    request: Request,
    limit: int = Query(20, ge=1, le=50),
    today_only: bool = Query(True),
) -> dict[str, Any]:
    since = today_madrid_start_unix() if today_only else None
    entries = list_marked_read(
        marked_read_path_for_db(_memory(request)._db_path),
        limit=limit,
        since=since,
    )
    return {"today_only": today_only, "entries": entries}


@router.post(
    "/gmail/messages/{message_id}/read",
    dependencies=[Depends(require_console_auth)],
)
async def gmail_mark_read(request: Request, message_id: str) -> dict[str, Any]:
    gmail = getattr(request.app.state, "gmail", None)
    if gmail is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="gmail_unavailable")
    try:
        ok = await gmail.mark_read(message_id, reason="manual")
    except GmailNotConnectedError:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="gmail_not_connected") from None
    except GmailConfigError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from None
    except GmailApiError as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail={"code": exc.code, "message": exc.message},
        ) from None
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="message_not_found")
    return {"ok": True, "message_id": message_id}


def _gmail_oauth_result_page(*, ok: bool, detail: str) -> HTMLResponse:
    title = "Gmail conectado" if ok else "Gmail — error"
    body = (
        f"<p>Cuenta: <strong>{detail}</strong></p><p>Ya puedes cerrar esta pestaña.</p>"
        if ok
        else f"<p>No se pudo conectar: <code>{detail}</code></p>"
    )
    html = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><title>{title}</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:28rem;margin:3rem auto;padding:0 1rem;line-height:1.45}}
a{{color:inherit}}
</style></head>
<body>
<h1>{title}</h1>
{body}
<p><a href="/">Volver a Kore</a></p>
<script>try{{window.opener&&window.opener.postMessage({{type:'kore-gmail',ok:{str(ok).lower()}}},'*')}}catch(e){{}}</script>
</body></html>"""
    return HTMLResponse(html, status_code=200 if ok else 400)
