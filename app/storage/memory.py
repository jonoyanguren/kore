"""Persistent companion memory: categorical facts, diary, and session chat."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import aiosqlite

from app.timeutil import session_date_str


@dataclass(frozen=True)
class TaskRow:
    id: int
    title: str
    status: str
    due_at: str | None
    priority: int
    notes: str | None = None
    url: str | None = None
    project: str | None = None


ACTIVE_TASK_STATUSES = ("open", "in_progress")
VALID_TASK_STATUSES = ("open", "in_progress", "done", "cancelled")

MISSION_ACTIVE_STATUSES = ("draft", "clarifying", "queued", "running", "waiting")
MISSION_DONE_STATUSES = ("done", "failed", "cancelled")
VALID_MISSION_STATUSES = MISSION_ACTIVE_STATUSES + MISSION_DONE_STATUSES


@dataclass(frozen=True)
class MissionRow:
    id: int
    title: str
    status: str
    brief: str
    plan_json: str | None
    step_index: int
    max_ticks: int
    tick_seconds: int
    next_run_at: str | None
    result_path: str | None
    error: str | None
    created_at: str
    updated_at: str

_STATUS_ES = {
    "open": "abierta",
    "in_progress": "en curso",
    "done": "hecha",
    "cancelled": "cancelada",
}


def format_task_block(task: TaskRow) -> list[str]:
    """One task as readable plain-text block (Telegram-friendly)."""
    lines = [f"{task.id}. {task.title}"]
    meta: list[str] = [_STATUS_ES.get(task.status, task.status)]
    if task.project:
        meta.append(task.project)
    if task.due_at:
        meta.append(task.due_at)
    if task.priority and task.priority > 0:
        meta.append(f"prio {task.priority}")
    lines.append("   " + " · ".join(meta))
    if task.url:
        lines.append(f"   {task.url}")
    if task.notes:
        note = task.notes.strip()
        if len(note) > 160:
            note = note[:157] + "…"
        lines.append(f"   {note}")
    return lines


def format_task_lines(tasks: list[TaskRow], *, detailed: bool = True) -> list[str]:
    """Plain-text lines for Telegram / tools (blank line between tasks)."""
    if not tasks:
        return []
    lines: list[str] = []
    for i, task in enumerate(tasks):
        if i:
            lines.append("")
        block = format_task_block(task)
        if not detailed:
            # title + meta only
            lines.extend(block[:2])
        else:
            lines.extend(block)
    return lines


def format_tasks_message(
    tasks: list[TaskRow],
    *,
    heading: str = "Tareas",
    detailed: bool = True,
) -> str:
    """Full Telegram message: en curso first, then pendientes (open)."""
    if not tasks:
        return f"{heading}\n\nNinguna por ahora."

    in_progress = [t for t in tasks if t.status == "in_progress"]
    pending = [t for t in tasks if t.status == "open"]
    other = [t for t in tasks if t.status not in ("in_progress", "open")]

    parts: list[str] = [heading]
    if in_progress:
        parts.append("")
        parts.append("En curso")
        parts.append("\n".join(format_task_lines(in_progress, detailed=detailed)))
    if pending:
        parts.append("")
        parts.append("Pendientes")
        parts.append("\n".join(format_task_lines(pending, detailed=detailed)))
    if other:
        parts.append("")
        parts.append("Otras")
        parts.append("\n".join(format_task_lines(other, detailed=detailed)))

    if not in_progress and not pending and not other:
        parts.append("")
        parts.append("Ninguna por ahora.")

    return "\n".join(parts).strip() + "\n"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS memory_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    text TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'chat',
    source_ref TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS diary_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    day TEXT NOT NULL,
    text TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'chat',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    session_date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    due_at TEXT,
    priority INTEGER NOT NULL DEFAULT 0,
    notes TEXT,
    url TEXT,
    project TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS agenda_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    starts_at TEXT NOT NULL,
    ends_at TEXT,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'planned',
    source TEXT NOT NULL DEFAULT 'chat',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS jobs (
    name TEXT PRIMARY KEY,
    last_run_at TEXT,
    last_status TEXT,
    last_error TEXT
);

CREATE TABLE IF NOT EXISTS missions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    brief TEXT NOT NULL DEFAULT '',
    plan_json TEXT,
    step_index INTEGER NOT NULL DEFAULT 0,
    max_ticks INTEGER NOT NULL DEFAULT 3,
    tick_seconds INTEGER NOT NULL DEFAULT 30,
    next_run_at TEXT,
    result_path TEXT,
    error TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS mission_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mission_id INTEGER NOT NULL,
    kind TEXT NOT NULL,
    payload TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (mission_id) REFERENCES missions(id)
);

CREATE TABLE IF NOT EXISTS llm_spend (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    day TEXT NOT NULL,
    kind TEXT NOT NULL,
    ref TEXT,
    model TEXT NOT NULL DEFAULT '',
    prompt_tokens INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    usd REAL NOT NULL DEFAULT 0,
    estimated INTEGER NOT NULL DEFAULT 0,
    session_id TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_memory_items_category ON memory_items(category);
CREATE INDEX IF NOT EXISTS idx_diary_entries_day ON diary_entries(day);
CREATE INDEX IF NOT EXISTS idx_messages_session_date ON messages(session_date);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_agenda_starts ON agenda_items(starts_at);
CREATE INDEX IF NOT EXISTS idx_missions_status ON missions(status);
CREATE INDEX IF NOT EXISTS idx_missions_next_run ON missions(next_run_at);
CREATE INDEX IF NOT EXISTS idx_mission_events_mission ON mission_events(mission_id);
CREATE INDEX IF NOT EXISTS idx_llm_spend_day ON llm_spend(day);
CREATE INDEX IF NOT EXISTS idx_llm_spend_kind ON llm_spend(kind);
CREATE INDEX IF NOT EXISTS idx_llm_spend_created ON llm_spend(created_at);
"""


class MemoryStore:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    async def init(self) -> None:
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self._db_path) as db:
            await db.executescript(SCHEMA_SQL)
            await self._migrate_notes(db)
            await self._migrate_task_columns(db)
            await db.commit()

    async def _migrate_task_columns(self, db: aiosqlite.Connection) -> None:
        cursor = await db.execute("PRAGMA table_info(tasks)")
        cols = {row[1] for row in await cursor.fetchall()}
        if "url" not in cols:
            await db.execute("ALTER TABLE tasks ADD COLUMN url TEXT")
        if "project" not in cols:
            await db.execute("ALTER TABLE tasks ADD COLUMN project TEXT")

    async def _migrate_notes(self, db: aiosqlite.Connection) -> None:
        """Copy legacy flat notes into memory_items (category=general), idempotent."""
        cursor = await db.execute("SELECT id, text FROM notes ORDER BY id")
        rows = await cursor.fetchall()
        for note_id, text in rows:
            source_ref = f"notes:{note_id}"
            existing = await db.execute(
                """
                SELECT 1 FROM memory_items
                WHERE source = 'migration' AND source_ref = ?
                """,
                (source_ref,),
            )
            if await existing.fetchone():
                continue
            await db.execute(
                """
                INSERT INTO memory_items (category, text, source, source_ref)
                VALUES (?, ?, 'migration', ?)
                """,
                ("general", text, source_ref),
            )

    # --- Categorical memory -------------------------------------------------

    async def save_memory(
        self,
        category: str,
        text: str,
        source: str = "chat",
        source_ref: str | None = None,
    ) -> int:
        category = (category or "general").strip().lower() or "general"
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO memory_items (category, text, source, source_ref)
                VALUES (?, ?, ?, ?)
                """,
                (category, text.strip(), source, source_ref),
            )
            await db.commit()
            return cursor.lastrowid

    async def list_memory(
        self, category: str | None = None, limit: int = 50
    ) -> list[tuple[int, str, str]]:
        async with aiosqlite.connect(self._db_path) as db:
            if category:
                cursor = await db.execute(
                    """
                    SELECT id, category, text FROM memory_items
                    WHERE category = ?
                    ORDER BY id DESC LIMIT ?
                    """,
                    (category.strip().lower(), limit),
                )
            else:
                cursor = await db.execute(
                    """
                    SELECT id, category, text FROM memory_items
                    ORDER BY id DESC LIMIT ?
                    """,
                    (limit,),
                )
            rows = await cursor.fetchall()
            return [(row[0], row[1], row[2]) for row in rows]

    async def memory_digests(
        self, limit_per_category: int = 8
    ) -> dict[str, list[tuple[int, str]]]:
        """Latest items grouped by category for the system prompt."""
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                "SELECT DISTINCT category FROM memory_items ORDER BY category"
            )
            categories = [row[0] for row in await cursor.fetchall()]
            digests: dict[str, list[tuple[int, str]]] = {}
            for category in categories:
                cursor = await db.execute(
                    """
                    SELECT id, text FROM memory_items
                    WHERE category = ?
                    ORDER BY id DESC LIMIT ?
                    """,
                    (category, limit_per_category),
                )
                items = [(row[0], row[1]) for row in await cursor.fetchall()]
                # Show oldest→newest within the digest window
                digests[category] = list(reversed(items))
            return digests

    async def delete_memory(self, item_id: int) -> bool:
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                "DELETE FROM memory_items WHERE id = ?", (item_id,)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def delete_memory_category(self, category: str) -> int:
        """Hard-delete all memory items in category. Returns rows deleted."""
        category = (category or "").strip().lower()
        if not category:
            return 0
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                "DELETE FROM memory_items WHERE category = ?",
                (category,),
            )
            await db.commit()
            return int(cursor.rowcount or 0)

    async def memory_category_counts(self) -> list[tuple[str, int]]:
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                """
                SELECT category, COUNT(*) FROM memory_items
                GROUP BY category
                ORDER BY category
                """
            )
            rows = await cursor.fetchall()
            return [(str(row[0]), int(row[1])) for row in rows]

    async def get_memory(self, item_id: int) -> tuple[int, str, str] | None:
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                "SELECT id, category, text FROM memory_items WHERE id = ?",
                (item_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            return (int(row[0]), row[1], row[2])

    # --- Diary --------------------------------------------------------------

    async def add_diary_entry(
        self, text: str, day: str | None = None, source: str = "chat"
    ) -> int:
        day = day or session_date_str()
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO diary_entries (day, text, source)
                VALUES (?, ?, ?)
                """,
                (day, text.strip(), source),
            )
            await db.commit()
            return cursor.lastrowid

    async def list_diary_for_day(self, day: str | None = None) -> list[tuple[int, str]]:
        day = day or session_date_str()
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                """
                SELECT id, text FROM diary_entries
                WHERE day = ?
                ORDER BY id
                """,
                (day,),
            )
            rows = await cursor.fetchall()
            return [(row[0], row[1]) for row in rows]

    async def delete_diary_entry(self, entry_id: int) -> str | None:
        """Delete diary row; return its day if deleted, else None."""
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                "SELECT day FROM diary_entries WHERE id = ?",
                (entry_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            day = row[0]
            await db.execute("DELETE FROM diary_entries WHERE id = ?", (entry_id,))
            await db.commit()
            return day

    # --- Session messages ---------------------------------------------------

    async def add_message(self, role: str, content: str, session_date: str | None = None) -> None:
        session_date = session_date or session_date_str()
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                INSERT INTO messages (role, content, session_date)
                VALUES (?, ?, ?)
                """,
                (role, content, session_date),
            )
            await db.commit()

    async def recent_messages(
        self, limit: int = 20, session_date: str | None = None
    ) -> list[tuple[str, str]]:
        session_date = session_date or session_date_str()
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                """
                SELECT role, content FROM messages
                WHERE session_date = ?
                ORDER BY id DESC LIMIT ?
                """,
                (session_date, limit),
            )
            rows = await cursor.fetchall()
            return [(row[0], row[1]) for row in reversed(rows)]

    async def list_messages_for_day(
        self, day: str | None = None, limit: int = 500
    ) -> list[tuple[str, str]]:
        """Session messages for a Madrid day, oldest→newest.

        When capped by `limit`, keeps the **most recent** N (not the oldest).
        """
        day = day or session_date_str()
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                """
                SELECT role, content FROM (
                    SELECT id, role, content FROM messages
                    WHERE session_date = ?
                    ORDER BY id DESC
                    LIMIT ?
                ) AS recent
                ORDER BY id ASC
                """,
                (day, limit),
            )
            rows = await cursor.fetchall()
            return [(row[0], row[1]) for row in rows]

    async def list_recent_messages(
        self, limit: int = 100, *, before_id: int | None = None
    ) -> list[tuple[int, str, str, str]]:
        """Last N messages across days: (id, role, content, created_at) oldest→newest.

        If `before_id` is set, return the N messages immediately older than that id.
        """
        async with aiosqlite.connect(self._db_path) as db:
            if before_id is None:
                cursor = await db.execute(
                    """
                    SELECT id, role, content, created_at FROM (
                        SELECT id, role, content, created_at FROM messages
                        ORDER BY id DESC
                        LIMIT ?
                    ) AS recent
                    ORDER BY id ASC
                    """,
                    (limit,),
                )
            else:
                cursor = await db.execute(
                    """
                    SELECT id, role, content, created_at FROM (
                        SELECT id, role, content, created_at FROM messages
                        WHERE id < ?
                        ORDER BY id DESC
                        LIMIT ?
                    ) AS older
                    ORDER BY id ASC
                    """,
                    (before_id, limit),
                )
            rows = await cursor.fetchall()
            return [(int(row[0]), row[1], row[2], row[3]) for row in rows]

    async def count_messages_before(self, before_id: int) -> int:
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM messages WHERE id < ?",
                (before_id,),
            )
            row = await cursor.fetchone()
            return int(row[0]) if row else 0

    async def count_messages(self) -> int:
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM messages")
            row = await cursor.fetchone()
            return int(row[0]) if row else 0

    # --- Legacy notes API (kept for migration / forget_note compat) ---------

    async def add_note(self, text: str) -> int:
        return await self.save_memory("general", text, source="note")

    async def list_notes(self) -> list[tuple[int, str]]:
        items = await self.list_memory(limit=100)
        return [(item_id, text) for item_id, _category, text in items]

    async def delete_note(self, note_id: int) -> bool:
        return await self.delete_memory(note_id)

    # --- Tasks --------------------------------------------------------------

    async def add_task(
        self,
        title: str,
        *,
        due_at: str | None = None,
        priority: int = 0,
        notes: str | None = None,
        url: str | None = None,
        project: str | None = None,
        status: str = "open",
    ) -> int:
        status = (status or "open").strip().lower()
        if status not in VALID_TASK_STATUSES:
            status = "open"
        project = (project or "").strip().lower() or None
        url = (url or "").strip() or None
        notes = (notes or "").strip() or None
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO tasks (title, status, due_at, priority, notes, url, project)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    title.strip(),
                    status,
                    due_at,
                    int(priority),
                    notes,
                    url,
                    project,
                ),
            )
            await db.commit()
            return cursor.lastrowid

    async def get_task(self, task_id: int) -> TaskRow | None:
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                """
                SELECT id, title, status, due_at, priority, notes, url, project
                FROM tasks WHERE id = ?
                """,
                (task_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            return TaskRow(*row)

    async def list_tasks(
        self,
        status: str | None = "open",
        limit: int = 30,
        *,
        project: str | None = None,
    ) -> list[TaskRow]:
        """status: open (= open+in_progress), in_progress, done, cancelled, all."""
        async with aiosqlite.connect(self._db_path) as db:
            clauses: list[str] = []
            params: list[object] = []
            if status and status != "all":
                st = status.strip().lower()
                if st == "open":
                    placeholders = ",".join("?" * len(ACTIVE_TASK_STATUSES))
                    clauses.append(f"status IN ({placeholders})")
                    params.extend(ACTIVE_TASK_STATUSES)
                else:
                    clauses.append("status = ?")
                    params.append(st)
            if project:
                clauses.append("project = ?")
                params.append(project.strip().lower())
            where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
            params.append(limit)
            cursor = await db.execute(
                f"""
                SELECT id, title, status, due_at, priority, notes, url, project
                FROM tasks
                {where}
                ORDER BY
                    CASE status
                        WHEN 'in_progress' THEN 0
                        WHEN 'open' THEN 1
                        ELSE 2
                    END,
                    priority DESC,
                    CASE WHEN due_at IS NULL THEN 1 ELSE 0 END,
                    due_at ASC,
                    id ASC
                LIMIT ?
                """,
                params,
            )
            rows = await cursor.fetchall()
            return [TaskRow(*row) for row in rows]

    async def update_task(
        self,
        task_id: int,
        *,
        title: str | None = None,
        status: str | None = None,
        due_at: str | None = None,
        priority: int | None = None,
        notes: str | None = None,
        url: str | None = None,
        project: str | None = None,
        clear_due: bool = False,
        clear_url: bool = False,
        clear_notes: bool = False,
        clear_project: bool = False,
    ) -> bool:
        task = await self.get_task(task_id)
        if task is None:
            return False
        new_status = task.status
        if status is not None:
            new_status = status.strip().lower()
            if new_status not in VALID_TASK_STATUSES:
                return False
        new_title = title.strip() if title is not None else task.title
        new_due = None if clear_due else (due_at if due_at is not None else task.due_at)
        new_prio = int(priority) if priority is not None else task.priority
        new_notes = None if clear_notes else (notes if notes is not None else task.notes)
        new_url = None if clear_url else (url if url is not None else task.url)
        if clear_project:
            new_project = None
        elif project is not None:
            new_project = project.strip().lower() or None
        else:
            new_project = task.project
        if isinstance(new_notes, str):
            new_notes = new_notes.strip() or None
        if isinstance(new_url, str):
            new_url = new_url.strip() or None
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                """
                UPDATE tasks SET
                    title = ?, status = ?, due_at = ?, priority = ?,
                    notes = ?, url = ?, project = ?,
                    updated_at = datetime('now')
                WHERE id = ?
                """,
                (
                    new_title,
                    new_status,
                    new_due,
                    new_prio,
                    new_notes,
                    new_url,
                    new_project,
                    task_id,
                ),
            )
            await db.commit()
            return cursor.rowcount > 0

    async def complete_task(self, task_id: int) -> bool:
        return await self.update_task(task_id, status="done")

    async def delete_task(self, task_id: int) -> bool:
        """Soft-delete: status=cancelled."""
        return await self.update_task(task_id, status="cancelled")

    async def purge_done_tasks(self) -> int:
        """Hard-delete all tasks with status=done. Returns rows removed."""
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute("DELETE FROM tasks WHERE status = 'done'")
            await db.commit()
            return int(cursor.rowcount or 0)

    async def list_and_purge_done_tasks(self) -> list[TaskRow]:
        """Return done tasks then hard-delete them (for vault archive)."""
        rows = await self.list_tasks(status="done", limit=200)
        if not rows:
            return []
        await self.purge_done_tasks()
        return rows

    # --- Agenda -------------------------------------------------------------

    async def add_agenda_item(
        self,
        title: str,
        starts_at: str,
        *,
        ends_at: str | None = None,
        source: str = "chat",
    ) -> int:
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO agenda_items (starts_at, ends_at, title, source)
                VALUES (?, ?, ?, ?)
                """,
                (starts_at.strip(), ends_at, title.strip(), source),
            )
            await db.commit()
            return cursor.lastrowid

    async def list_agenda_upcoming(
        self,
        from_day: str | None = None,
        limit: int = 20,
        *,
        to_day: str | None = None,
    ) -> list[tuple[int, str, str, str]]:
        """Return (id, starts_at, title, status) from from_day onward.

        If to_day is set (YYYY-MM-DD), only include items with starts_at date <= to_day.
        """
        from datetime import date as date_cls
        from datetime import timedelta

        from_day = from_day or session_date_str()
        async with aiosqlite.connect(self._db_path) as db:
            if to_day:
                end = (date_cls.fromisoformat(to_day) + timedelta(days=1)).isoformat()
                cursor = await db.execute(
                    """
                    SELECT id, starts_at, title, status FROM agenda_items
                    WHERE starts_at >= ? AND starts_at < ? AND status != 'cancelled'
                    ORDER BY starts_at ASC, id ASC
                    LIMIT ?
                    """,
                    (from_day, end, limit),
                )
            else:
                cursor = await db.execute(
                    """
                    SELECT id, starts_at, title, status FROM agenda_items
                    WHERE starts_at >= ? AND status != 'cancelled'
                    ORDER BY starts_at ASC, id ASC
                    LIMIT ?
                    """,
                    (from_day, limit),
                )
            rows = await cursor.fetchall()
            return [(row[0], row[1], row[2], row[3]) for row in rows]

    async def list_agenda_for_month(
        self, month: str
    ) -> list[tuple[int, str, str, str]]:
        """month = YYYY-MM. Return (id, starts_at, title, status)."""
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                """
                SELECT id, starts_at, title, status FROM agenda_items
                WHERE starts_at LIKE ? AND status != 'cancelled'
                ORDER BY starts_at ASC, id ASC
                """,
                (f"{month}%",),
            )
            rows = await cursor.fetchall()
            return [(row[0], row[1], row[2], row[3]) for row in rows]

    # --- Missions -----------------------------------------------------------

    def _mission_from_row(self, row: tuple) -> MissionRow:
        return MissionRow(
            id=row[0],
            title=row[1],
            status=row[2],
            brief=row[3] or "",
            plan_json=row[4],
            step_index=int(row[5] or 0),
            max_ticks=int(row[6] or 3),
            tick_seconds=int(row[7] or 30),
            next_run_at=row[8],
            result_path=row[9],
            error=row[10],
            created_at=row[11],
            updated_at=row[12],
        )

    async def add_mission(
        self,
        title: str,
        *,
        brief: str = "",
        status: str = "draft",
        max_ticks: int = 3,
        tick_seconds: int = 30,
        next_run_at: str | None = None,
        result_path: str | None = None,
    ) -> int:
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO missions (
                    title, status, brief, max_ticks, tick_seconds,
                    next_run_at, result_path
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    title.strip(),
                    status,
                    brief.strip(),
                    max(1, max_ticks),
                    max(5, tick_seconds),
                    next_run_at,
                    result_path,
                ),
            )
            await db.commit()
            return int(cursor.lastrowid)

    async def get_mission(self, mission_id: int) -> MissionRow | None:
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                """
                SELECT id, title, status, brief, plan_json, step_index,
                       max_ticks, tick_seconds, next_run_at, result_path,
                       error, created_at, updated_at
                FROM missions WHERE id = ?
                """,
                (mission_id,),
            )
            row = await cursor.fetchone()
            return self._mission_from_row(row) if row else None

    async def list_missions(
        self,
        *,
        include_done: bool = True,
        limit: int = 50,
    ) -> list[MissionRow]:
        async with aiosqlite.connect(self._db_path) as db:
            if include_done:
                cursor = await db.execute(
                    """
                    SELECT id, title, status, brief, plan_json, step_index,
                           max_ticks, tick_seconds, next_run_at, result_path,
                           error, created_at, updated_at
                    FROM missions
                    ORDER BY
                      CASE status
                        WHEN 'running' THEN 0
                        WHEN 'waiting' THEN 1
                        WHEN 'queued' THEN 2
                        WHEN 'clarifying' THEN 3
                        WHEN 'draft' THEN 4
                        ELSE 5
                      END,
                      updated_at DESC,
                      id DESC
                    LIMIT ?
                    """,
                    (max(1, min(limit, 100)),),
                )
            else:
                placeholders = ",".join("?" for _ in MISSION_ACTIVE_STATUSES)
                cursor = await db.execute(
                    f"""
                    SELECT id, title, status, brief, plan_json, step_index,
                           max_ticks, tick_seconds, next_run_at, result_path,
                           error, created_at, updated_at
                    FROM missions
                    WHERE status IN ({placeholders})
                    ORDER BY
                      CASE status
                        WHEN 'running' THEN 0
                        WHEN 'waiting' THEN 1
                        WHEN 'queued' THEN 2
                        WHEN 'clarifying' THEN 3
                        WHEN 'draft' THEN 4
                        ELSE 5
                      END,
                      updated_at DESC,
                      id DESC
                    LIMIT ?
                    """,
                    (*MISSION_ACTIVE_STATUSES, max(1, min(limit, 100))),
                )
            rows = await cursor.fetchall()
            return [self._mission_from_row(r) for r in rows]

    async def update_mission(
        self,
        mission_id: int,
        *,
        title: str | None = None,
        status: str | None = None,
        brief: str | None = None,
        plan_json: str | None = None,
        step_index: int | None = None,
        max_ticks: int | None = None,
        tick_seconds: int | None = None,
        next_run_at: str | None = None,
        clear_next_run: bool = False,
        result_path: str | None = None,
        error: str | None = None,
        clear_error: bool = False,
    ) -> MissionRow | None:
        current = await self.get_mission(mission_id)
        if current is None:
            return None
        if status is not None and status not in VALID_MISSION_STATUSES:
            raise ValueError(f"invalid mission status: {status}")
        new_next = current.next_run_at
        if clear_next_run:
            new_next = None
        elif next_run_at is not None:
            new_next = next_run_at
        new_error = None if clear_error else current.error
        if error is not None:
            new_error = error
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                UPDATE missions SET
                    title = ?,
                    status = ?,
                    brief = ?,
                    plan_json = ?,
                    step_index = ?,
                    max_ticks = ?,
                    tick_seconds = ?,
                    next_run_at = ?,
                    result_path = ?,
                    error = ?,
                    updated_at = datetime('now')
                WHERE id = ?
                """,
                (
                    title if title is not None else current.title,
                    status if status is not None else current.status,
                    brief if brief is not None else current.brief,
                    plan_json if plan_json is not None else current.plan_json,
                    step_index if step_index is not None else current.step_index,
                    max_ticks if max_ticks is not None else current.max_ticks,
                    tick_seconds if tick_seconds is not None else current.tick_seconds,
                    new_next,
                    result_path if result_path is not None else current.result_path,
                    new_error,
                    mission_id,
                ),
            )
            await db.commit()
        return await self.get_mission(mission_id)

    async def add_mission_event(
        self,
        mission_id: int,
        kind: str,
        payload: str | None = None,
    ) -> int:
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO mission_events (mission_id, kind, payload)
                VALUES (?, ?, ?)
                """,
                (mission_id, kind, payload),
            )
            await db.commit()
            return int(cursor.lastrowid)

    async def list_due_missions(self, *, now_iso: str, limit: int = 5) -> list[MissionRow]:
        """Missions ready to tick (queued/waiting/running with next_run_at <= now)."""
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                """
                SELECT id, title, status, brief, plan_json, step_index,
                       max_ticks, tick_seconds, next_run_at, result_path,
                       error, created_at, updated_at
                FROM missions
                WHERE status IN ('queued', 'waiting', 'running')
                  AND next_run_at IS NOT NULL
                  AND next_run_at <= ?
                ORDER BY next_run_at ASC, id ASC
                LIMIT ?
                """,
                (now_iso, max(1, min(limit, 20))),
            )
            rows = await cursor.fetchall()
            return [self._mission_from_row(r) for r in rows]

    async def count_missions_in_status(self, *statuses: str) -> int:
        if not statuses:
            return 0
        placeholders = ",".join("?" for _ in statuses)
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                f"SELECT COUNT(*) FROM missions WHERE status IN ({placeholders})",
                statuses,
            )
            row = await cursor.fetchone()
            return int(row[0] if row else 0)

    # --- LLM spend ledger ---------------------------------------------------

    async def add_llm_spend(
        self,
        *,
        kind: str,
        model: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        usd: float = 0.0,
        estimated: bool = False,
        ref: str | None = None,
        session_id: str | None = None,
        day: str | None = None,
    ) -> int:
        day_v = (day or session_date_str()).strip()
        kind_v = (kind or "other").strip().lower() or "other"
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO llm_spend (
                    day, kind, ref, model, prompt_tokens, completion_tokens,
                    usd, estimated, session_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    day_v,
                    kind_v,
                    (ref or "").strip() or None,
                    (model or "").strip(),
                    max(0, int(prompt_tokens)),
                    max(0, int(completion_tokens)),
                    float(usd),
                    1 if estimated else 0,
                    (session_id or "").strip() or None,
                ),
            )
            await db.commit()
            return int(cursor.lastrowid)

    async def list_llm_spend(
        self,
        *,
        day_from: str | None = None,
        day_to: str | None = None,
        kind: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        clauses: list[str] = []
        params: list[object] = []
        if day_from:
            clauses.append("day >= ?")
            params.append(day_from)
        if day_to:
            clauses.append("day <= ?")
            params.append(day_to)
        if kind:
            clauses.append("kind = ?")
            params.append(kind.strip().lower())
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(max(1, min(int(limit), 500)))
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                f"""
                SELECT id, day, kind, ref, model, prompt_tokens, completion_tokens,
                       usd, estimated, session_id, created_at
                FROM llm_spend
                {where}
                ORDER BY id DESC
                LIMIT ?
                """,
                params,
            )
            rows = await cursor.fetchall()
        return [
            {
                "id": r[0],
                "day": r[1],
                "kind": r[2],
                "ref": r[3],
                "model": r[4],
                "prompt_tokens": int(r[5] or 0),
                "completion_tokens": int(r[6] or 0),
                "usd": float(r[7] or 0),
                "estimated": bool(r[8]),
                "session_id": r[9],
                "created_at": r[10],
            }
            for r in rows
        ]

    async def summarize_llm_spend(
        self,
        *,
        day_from: str | None = None,
        day_to: str | None = None,
    ) -> dict:
        """Totals overall + by day + by kind in the range."""
        clauses: list[str] = []
        params: list[object] = []
        if day_from:
            clauses.append("day >= ?")
            params.append(day_from)
        if day_to:
            clauses.append("day <= ?")
            params.append(day_to)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                f"""
                SELECT COALESCE(SUM(usd), 0), COALESCE(SUM(prompt_tokens), 0),
                       COALESCE(SUM(completion_tokens), 0), COUNT(*)
                FROM llm_spend {where}
                """,
                params,
            )
            total = await cursor.fetchone()
            cursor = await db.execute(
                f"""
                SELECT day, COALESCE(SUM(usd), 0), COUNT(*)
                FROM llm_spend {where}
                GROUP BY day
                ORDER BY day DESC
                """,
                params,
            )
            by_day = await cursor.fetchall()
            cursor = await db.execute(
                f"""
                SELECT kind, COALESCE(SUM(usd), 0), COUNT(*)
                FROM llm_spend {where}
                GROUP BY kind
                ORDER BY SUM(usd) DESC
                """,
                params,
            )
            by_kind = await cursor.fetchall()
        return {
            "usd": round(float(total[0] if total else 0), 4),
            "prompt_tokens": int(total[1] if total else 0),
            "completion_tokens": int(total[2] if total else 0),
            "calls": int(total[3] if total else 0),
            "by_day": [
                {"day": d, "usd": round(float(u), 4), "calls": int(c)}
                for d, u, c in by_day
            ],
            "by_kind": [
                {"kind": k, "usd": round(float(u), 4), "calls": int(c)}
                for k, u, c in by_kind
            ],
        }

    # --- Jobs (cron bookkeeping) --------------------------------------------

    async def get_job(self, name: str) -> tuple[str | None, str | None, str | None]:
        """Return (last_run_at, last_status, last_error)."""
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                "SELECT last_run_at, last_status, last_error FROM jobs WHERE name = ?",
                (name,),
            )
            row = await cursor.fetchone()
            if row is None:
                return None, None, None
            return row[0], row[1], row[2]

    async def mark_job(
        self,
        name: str,
        *,
        status: str,
        error: str | None = None,
        ran_at: str | None = None,
    ) -> None:
        ran_at = ran_at or session_date_str()
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                INSERT INTO jobs (name, last_run_at, last_status, last_error)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    last_run_at = excluded.last_run_at,
                    last_status = excluded.last_status,
                    last_error = excluded.last_error
                """,
                (name, ran_at, status, error),
            )
            await db.commit()

    async def list_memory_all_by_category(
        self, category: str
    ) -> list[tuple[int, str]]:
        """All items in category oldest→newest for vault rewrite."""
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                """
                SELECT id, text FROM memory_items
                WHERE category = ?
                ORDER BY id ASC
                """,
                (category.strip().lower(),),
            )
            rows = await cursor.fetchall()
            return [(row[0], row[1]) for row in rows]

    async def list_categories(self) -> list[str]:
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                "SELECT DISTINCT category FROM memory_items ORDER BY category"
            )
            return [row[0] for row in await cursor.fetchall()]
