"""Persistent notes store — the bot's durable memory across conversations.

SQLite-backed, single table. Not a full conversation-history system (that's
a separate, bigger feature) — just short facts/context the model should
always have available, e.g. "the 'Jon list' in ClickUp is for personal use".
"""

from __future__ import annotations

from pathlib import Path

import aiosqlite

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
)
"""


class MemoryStore:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    async def init(self) -> None:
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(CREATE_TABLE_SQL)
            await db.commit()

    async def add_note(self, text: str) -> int:
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute("INSERT INTO notes (text) VALUES (?)", (text,))
            await db.commit()
            return cursor.lastrowid

    async def list_notes(self) -> list[tuple[int, str]]:
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute("SELECT id, text FROM notes ORDER BY id")
            rows = await cursor.fetchall()
            return [(row[0], row[1]) for row in rows]

    async def delete_note(self, note_id: int) -> bool:
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute("DELETE FROM notes WHERE id = ?", (note_id,))
            await db.commit()
            return cursor.rowcount > 0
