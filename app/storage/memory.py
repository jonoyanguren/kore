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

CREATE INDEX IF NOT EXISTS idx_memory_items_category ON memory_items(category);
CREATE INDEX IF NOT EXISTS idx_diary_entries_day ON diary_entries(day);
CREATE INDEX IF NOT EXISTS idx_messages_session_date ON messages(session_date);
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

    # --- Legacy notes API (kept for migration / forget_note compat) ---------

    async def add_note(self, text: str) -> int:
        return await self.save_memory("general", text, source="note")

    async def list_notes(self) -> list[tuple[int, str]]:
        items = await self.list_memory(limit=100)
        return [(item_id, text) for item_id, _category, text in items]

    async def delete_note(self, note_id: int) -> bool:
        return await self.delete_memory(note_id)
