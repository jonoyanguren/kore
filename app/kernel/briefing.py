"""Day briefing: structured template from live tasks/agenda + dream help."""

from __future__ import annotations

import re
from datetime import date, timedelta
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
    "inbox": "inbox",
    "correo": "inbox",
    "mail": "inbox",
    "gmail": "inbox",
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
    if s.startswith("inbox") or s.startswith("correo") or s.startswith("gmail"):
        return "inbox"
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
        "inbox": [],
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
                if _normalize_header(line) in {
                    "skip",
                    "tasks",
                    "meetings",
                    "summary",
                    "inbox",
                }:
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
    """Legacy mix: in_progress first, then priority>0, then remaining open."""
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


def pick_in_progress_tasks(rows: list[TaskRow]) -> list[TaskRow]:
    """Starred / en curso — all of them for the Day strip."""
    return [t for t in rows if t.status == "in_progress"]


def _norm_title(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def _titles_match(live: str, hint: str) -> bool:
    a, b = _norm_title(live), _norm_title(hint)
    if not a or not b:
        return False
    if a == b or a in b or b in a:
        return True
    aw = {w for w in re.split(r"[^\wáéíóúñ]+", a) if len(w) > 3}
    bw = {w for w in re.split(r"[^\wáéíóúñ]+", b) if len(w) > 3}
    if not aw or not bw:
        return False
    return len(aw & bw) >= min(2, len(aw), len(bw))


def titles_match(live: str, hint: str) -> bool:
    """Public alias for task dedupe / dream / briefing."""
    return _titles_match(live, hint)

def pick_must_not_miss(
    rows: list[TaskRow],
    *,
    dream_task_titles: list[str] | None = None,
    today: str,
    limit: int = 5,
) -> list[TaskRow]:
    """Open tasks Jone would not let slip: dream hints, due soon, priority.

    Excludes in_progress (those belong in the star section).
    """
    hints = dream_task_titles or []
    horizon = (date.fromisoformat(today) + timedelta(days=2)).isoformat()
    scored: list[tuple[int, TaskRow]] = []
    for t in rows:
        if t.status != "open":
            continue
        score = 0
        if (t.priority or 0) > 0:
            score += 10 + int(t.priority)
        if t.due_at:
            due = t.due_at[:10]
            if due <= today:
                score += 25  # overdue / today
            elif due <= horizon:
                score += 12
        for hint in hints:
            if _titles_match(t.title, hint):
                score += 20
                break
        if score > 0:
            scored.append((score, t))
    scored.sort(key=lambda x: (-x[0], -(x[1].priority or 0), x[1].id))
    return [t for _, t in scored[:limit]]


def task_dict(t: TaskRow) -> dict[str, Any]:
    return {
        "id": t.id,
        "title": t.title,
        "status": t.status,
        "project": t.project,
        "due_at": t.due_at,
        "priority": t.priority,
    }


async def build_day_briefing(
    memory: Any,
    vault: Any,
    *,
    google_meetings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    today = session_date_str()
    yesterday = (today_madrid() - timedelta(days=1)).isoformat()

    dream_day = yesterday
    dream_raw = vault.read_dream(yesterday)
    if dream_raw is None:
        dream_day = today
        dream_raw = vault.read_dream(today)

    sections = parse_dream_sections(dream_raw)

    open_tasks = await memory.list_tasks(status="open", limit=80)
    in_progress = pick_in_progress_tasks(open_tasks)
    must_not_miss = pick_must_not_miss(
        open_tasks,
        dream_task_titles=sections["tasks"],
        today=today,
        limit=5,
    )
    # Back-compat for older clients / tests
    important = pick_important_tasks(open_tasks, limit=5)

    # Vista Día: solo ventana corta (hoy + 3 días). No meter citas de dentro de semanas.
    agenda_rows = await memory.list_agenda_upcoming(
        from_day=today,
        limit=6,
        to_day=(today_madrid() + timedelta(days=3)).isoformat(),
    )
    local_meetings = [
        {
            "id": i,
            "starts_at": starts,
            "title": title,
            "status": st,
            "source": "local",
        }
        for i, starts, title, st in agenda_rows
    ]

    from app.integrations.google_calendar.client import merge_meetings

    meetings = merge_meetings(local_meetings, google_meetings or [], limit=12)

    help_items = sections["help"]
    summary_items = sections["summary"]
    usable_dream = bool(dream_raw) and (
        bool(summary_items) or bool(help_items) or bool(sections["tasks"])
    )

    # Día never empty: if dream missing/thin, fill help from live state.
    if not help_items:
        live_help: list[str] = []
        if in_progress:
            live_help.append(
                "En curso: " + ", ".join(t.title for t in in_progress[:3])
            )
        if must_not_miss:
            live_help.append(
                "No dejar pasar: " + ", ".join(t.title for t in must_not_miss[:3])
            )
        if meetings:
            m0 = meetings[0]
            live_help.append(
                f"Próxima: {m0.get('starts_at', '')} — {m0.get('title', '')}".strip(
                    " —"
                )
            )
        if not live_help:
            if not dream_raw:
                live_help.append(
                    "Sin dream aún — cron 09:00 o /dream en el chat de la consola"
                )
            else:
                live_help.append("Dream sin notas de ayuda — revisa tareas y reuniones")
        help_items = live_help[:6]

    if not summary_items and not usable_dream:
        bits = []
        if in_progress:
            bits.append(f"{len(in_progress)} en curso")
        if must_not_miss:
            bits.append(f"{len(must_not_miss)} a no dejar pasar")
        if meetings:
            bits.append(f"{len(meetings)} reuniones")
        summary_items = [
            " · ".join(bits) if bits else "Día sin dream — datos vivos abajo"
        ]

    return {
        "day": dream_day if dream_raw else None,
        "has_dream": bool(dream_raw) and usable_dream,
        "dream_present": bool(dream_raw),
        "summary": summary_items,
        "in_progress_tasks": [task_dict(t) for t in in_progress],
        "must_not_miss": [task_dict(t) for t in must_not_miss],
        "important_tasks": [task_dict(t) for t in important],
        "meetings": meetings,
        "help": help_items,
        "inbox": sections["inbox"],
    }
