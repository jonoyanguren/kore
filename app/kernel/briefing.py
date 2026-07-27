"""Day briefing: structured template from live tasks/agenda + dream help."""

from __future__ import annotations

import re
from datetime import timedelta
from typing import Any

from app.storage.memory import TaskRow
from app.timeutil import session_date_str, today_madrid

_SECTION_HEADERS = {
    "ayuda": "help",
    "help": "help",
    "foco": "help",
    "prep": "help",
    "prep de hoy": "help",
    "c)": "help",
    "cierre": "skip",
    "resumen": "summary",
    "huecos": "skip",
    "tareas importantes": "tasks",
    "tareas": "tasks",
    "reuniones": "meetings",
    "agenda": "meetings",
}


def _normalize_header(line: str) -> str | None:
    s = line.strip()
    s = re.sub(r"^#+\s*", "", s)
    s = re.sub(r"^[*_]+|[*_]+$", "", s)
    s = s.rstrip(":").strip().lower()
    # "A) Resumen" / "C) Prep..."
    s = re.sub(r"^[a-d]\)\s*", "", s)
    if s in _SECTION_HEADERS:
        return _SECTION_HEADERS[s]
    if s.startswith("prep"):
        return "help"
    if s.startswith("tarea"):
        return "tasks"
    if s.startswith("reunion") or s.startswith("reunión"):
        return "meetings"
    if s.startswith("ayuda") or s.startswith("foco"):
        return "help"
    return None


def _bullet_or_line(line: str) -> str | None:
    s = line.strip()
    if not s or s.startswith("#"):
        return None
    if _normalize_header(s) is not None:
        return None
    s = re.sub(r"^[-*•]\s+", "", s)
    s = re.sub(r"^\d+[.)]\s+", "", s)
    s = s.strip()
    if not s or s.lower() in {"ninguna", "ninguno", "nada", "n/a", "(nada)"}:
        return None
    return s


def parse_dream_sections(raw: str | None) -> dict[str, list[str]]:
    """Split dream markdown/plain into summary / help / tasks / meetings."""
    out: dict[str, list[str]] = {
        "summary": [],
        "help": [],
        "tasks": [],
        "meetings": [],
    }
    if not raw:
        return out

    current: str | None = None
    for line in raw.splitlines():
        kind = _normalize_header(line)
        if kind == "skip":
            current = None
            continue
        if kind is not None:
            current = kind
            continue
        if current is None:
            continue
        item = _bullet_or_line(line)
        if item:
            out[current].append(item)

    # Fallback: if no labeled help, take non-header lines after "prep"/"hoy" cues
    if not out["help"]:
        blob = []
        grab = False
        for line in raw.splitlines():
            low = line.strip().lower()
            if re.search(r"\bprep\b|\bfoco\b|\bayuda\b", low) and len(low) < 40:
                grab = True
                continue
            if grab:
                if _normalize_header(line) in {"skip", "tasks", "meetings", "summary"}:
                    break
                item = _bullet_or_line(line)
                if item:
                    blob.append(item)
        out["help"] = blob[:6]

    for k in out:
        # dedupe preserve order
        seen: set[str] = set()
        uniq: list[str] = []
        for x in out[k]:
            key = x.lower()
            if key in seen:
                continue
            seen.add(key)
            uniq.append(x)
        out[k] = uniq[:8]
    return out

def pick_important_tasks(rows: list[TaskRow], *, limit: int = 5) -> list[TaskRow]:
    """in_progress first, then priority>0, then remaining open."""
    progress = [t for t in rows if t.status == "in_progress"]
    prio_ids = {t.id for t in progress}
    prio = [
        t
        for t in rows
        if t.status == "open" and (t.priority or 0) > 0 and t.id not in prio_ids
    ]
    prio_ids.update(t.id for t in prio)
    rest = [t for t in rows if t.status == "open" and t.id not in prio_ids]
    return (progress + prio + rest)[:limit]


def task_dict(t: TaskRow) -> dict[str, Any]:
    return {
        "id": t.id,
        "title": t.title,
        "status": t.status,
        "project": t.project,
        "due_at": t.due_at,
        "priority": t.priority,
    }


async def build_day_briefing(memory: Any, vault: Any) -> dict[str, Any]:
    today = session_date_str()
    yesterday = (today_madrid() - timedelta(days=1)).isoformat()

    dream_day = yesterday
    dream_raw = vault.read_dream(yesterday)
    if dream_raw is None:
        dream_day = today
        dream_raw = vault.read_dream(today)

    sections = parse_dream_sections(dream_raw)

    open_tasks = await memory.list_tasks(status="open", limit=80)
    important = pick_important_tasks(open_tasks, limit=5)

    # Vista Día: solo ventana corta (hoy + 3 días). No meter citas de dentro de semanas.
    agenda_rows = await memory.list_agenda_upcoming(
        from_day=today,
        limit=6,
        to_day=(today_madrid() + timedelta(days=3)).isoformat(),
    )
    meetings = [
        {
            "id": i,
            "starts_at": starts,
            "title": title,
            "status": st,
        }
        for i, starts, title, st in agenda_rows
    ]

    help_items = sections["help"]
    # If dream listed task titles as text and we have none live, keep dream tasks as help-ish notes
    if not important and sections["tasks"]:
        # surface dream task lines under help as soft hints only if empty help
        if not help_items:
            help_items = [f"Pendiente (dream): {t}" for t in sections["tasks"][:4]]

    return {
        "day": dream_day if dream_raw else None,
        "has_dream": bool(dream_raw),
        "summary": sections["summary"],
        "important_tasks": [task_dict(t) for t in important],
        "meetings": meetings,
        "help": help_items,
    }
