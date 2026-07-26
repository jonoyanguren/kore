"""Persistent companion memory: categorical facts, diary, and session chat."""

from __future__ import annotations

from pathlib import Path

import aiosqlite

from app.timeutil import session_date_str

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

CREATE INDEX IF NOT EXISTS idx_memory_items_category ON memory_items(category);
CREATE INDEX IF NOT EXISTS idx_diary_entries_day ON diary_entries(day);
CREATE INDEX IF NOT EXISTS idx_messages_session_date ON messages(session_date);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_agenda_starts ON agenda_items(starts_at);
"""


class MemoryStore:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    async def init(self) -> None:
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self._db_path) as db:
            await db.executescript(SCHEMA_SQL)
            await self._migrate_notes(db)
            await db.commit()

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
        """All session messages for a Madrid day, oldest→newest (capped)."""
        day = day or session_date_str()
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                """
                SELECT role, content FROM messages
                WHERE session_date = ?
                ORDER BY id ASC
                LIMIT ?
                """,
                (day, limit),
            )
            rows = await cursor.fetchall()
            return [(row[0], row[1]) for row in rows]

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
    ) -> int:
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO tasks (title, due_at, priority, notes)
                VALUES (?, ?, ?, ?)
                """,
                (title.strip(), due_at, int(priority), notes),
            )
            await db.commit()
            return cursor.lastrowid

    async def list_tasks(
        self, status: str | None = "open", limit: int = 30
    ) -> list[tuple[int, str, str, str | None, int]]:
        """Return (id, title, status, due_at, priority)."""
        async with aiosqlite.connect(self._db_path) as db:
            if status:
                cursor = await db.execute(
                    """
                    SELECT id, title, status, due_at, priority FROM tasks
                    WHERE status = ?
                    ORDER BY
                        CASE WHEN due_at IS NULL THEN 1 ELSE 0 END,
                        due_at ASC,
                        priority DESC,
                        id ASC
                    LIMIT ?
                    """,
                    (status.strip().lower(), limit),
                )
            else:
                cursor = await db.execute(
                    """
                    SELECT id, title, status, due_at, priority FROM tasks
                    ORDER BY id DESC LIMIT ?
                    """,
                    (limit,),
                )
            rows = await cursor.fetchall()
            return [
                (row[0], row[1], row[2], row[3], row[4]) for row in rows
            ]

    async def complete_task(self, task_id: int) -> bool:
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                """
                UPDATE tasks
                SET status = 'done', updated_at = datetime('now')
                WHERE id = ? AND status != 'done'
                """,
                (task_id,),
            )
            await db.commit()
            return cursor.rowcount > 0

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
        self, from_day: str | None = None, limit: int = 20
    ) -> list[tuple[int, str, str, str]]:
        """Return (id, starts_at, title, status) from from_day onward."""
        from_day = from_day or session_date_str()
        async with aiosqlite.connect(self._db_path) as db:
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
