"""Shared accounts DB: users + sessions. Not memory/tasks/vault."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import aiosqlite

from app.accounts.context import CompanionProfile
from app.accounts.passwords import hash_password, verify_password

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    owner_name TEXT NOT NULL DEFAULT '',
    companion_name TEXT NOT NULL DEFAULT '',
    companion_tone TEXT NOT NULL DEFAULT '',
    legacy_prompts INTEGER NOT NULL DEFAULT 0,
    onboarded INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
"""

SESSION_DAYS = 30


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat()


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


@dataclass(frozen=True)
class UserRow:
    id: int
    email: str
    owner_name: str
    companion_name: str
    companion_tone: str
    legacy_prompts: bool
    onboarded: bool

    def profile(self) -> CompanionProfile:
        return CompanionProfile(
            user_id=self.id,
            email=self.email,
            owner_name=self.owner_name,
            companion_name=self.companion_name,
            companion_tone=self.companion_tone,
            legacy_prompts=self.legacy_prompts,
            onboarded=self.onboarded,
        )


class AccountStore:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    async def init(self) -> None:
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self._db_path) as db:
            await db.executescript(SCHEMA)
            await db.commit()

    def _row(self, row: tuple) -> UserRow:
        return UserRow(
            id=int(row[0]),
            email=row[1],
            owner_name=row[2] or "",
            companion_name=row[3] or "",
            companion_tone=row[4] or "",
            legacy_prompts=bool(row[5]),
            onboarded=bool(row[6]),
        )

    _COLS = (
        "id, email, owner_name, companion_name, companion_tone, "
        "legacy_prompts, onboarded"
    )

    async def create_user(
        self,
        *,
        email: str,
        password: str,
        owner_name: str = "",
        companion_name: str = "",
        companion_tone: str = "",
        legacy_prompts: bool = False,
        onboarded: bool = False,
    ) -> UserRow:
        email_n = normalize_email(email)
        if not email_n or "@" not in email_n:
            raise ValueError("email inválido")
        if len(password) < 8:
            raise ValueError("la contraseña debe tener al menos 8 caracteres")
        async with aiosqlite.connect(self._db_path) as db:
            try:
                cur = await db.execute(
                    f"""
                    INSERT INTO users (
                        email, password_hash, owner_name, companion_name,
                        companion_tone, legacy_prompts, onboarded
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    RETURNING {self._COLS}
                    """,
                    (
                        email_n,
                        hash_password(password),
                        owner_name.strip(),
                        companion_name.strip(),
                        companion_tone.strip(),
                        1 if legacy_prompts else 0,
                        1 if onboarded else 0,
                    ),
                )
                row = await cur.fetchone()
                await db.commit()
            except aiosqlite.IntegrityError as exc:
                raise ValueError("ese email ya está registrado") from exc
        assert row is not None
        return self._row(row)

    async def get_user(self, user_id: int) -> UserRow | None:
        async with aiosqlite.connect(self._db_path) as db:
            cur = await db.execute(
                f"SELECT {self._COLS} FROM users WHERE id = ?",
                (user_id,),
            )
            row = await cur.fetchone()
            return self._row(row) if row else None

    async def get_by_email(self, email: str) -> UserRow | None:
        async with aiosqlite.connect(self._db_path) as db:
            cur = await db.execute(
                f"SELECT {self._COLS} FROM users WHERE email = ?",
                (normalize_email(email),),
            )
            row = await cur.fetchone()
            return self._row(row) if row else None

    async def count_users(self) -> int:
        async with aiosqlite.connect(self._db_path) as db:
            cur = await db.execute("SELECT COUNT(*) FROM users")
            row = await cur.fetchone()
            return int(row[0]) if row else 0

    async def list_user_ids(self) -> list[int]:
        async with aiosqlite.connect(self._db_path) as db:
            cur = await db.execute("SELECT id FROM users ORDER BY id")
            rows = await cur.fetchall()
            return [int(r[0]) for r in rows]

    async def legacy_user(self) -> UserRow | None:
        async with aiosqlite.connect(self._db_path) as db:
            cur = await db.execute(
                f"SELECT {self._COLS} FROM users WHERE legacy_prompts = 1 "
                "ORDER BY id LIMIT 1"
            )
            row = await cur.fetchone()
            return self._row(row) if row else None

    async def authenticate(self, email: str, password: str) -> UserRow | None:
        email_n = normalize_email(email)
        async with aiosqlite.connect(self._db_path) as db:
            cur = await db.execute(
                f"SELECT {self._COLS}, password_hash FROM users WHERE email = ?",
                (email_n,),
            )
            row = await cur.fetchone()
        if row is None:
            return None
        if not verify_password(password, row[7]):
            return None
        return self._row(row[:7])

    async def update_companion(
        self,
        user_id: int,
        *,
        owner_name: str | None = None,
        companion_name: str | None = None,
        companion_tone: str | None = None,
        onboarded: bool | None = None,
    ) -> UserRow | None:
        current = await self.get_user(user_id)
        if current is None:
            return None
        new_owner = current.owner_name if owner_name is None else owner_name.strip()
        new_name = (
            current.companion_name
            if companion_name is None
            else companion_name.strip()
        )
        new_tone = (
            current.companion_tone
            if companion_tone is None
            else companion_tone.strip()
        )
        new_on = current.onboarded if onboarded is None else onboarded
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                UPDATE users SET
                    owner_name = ?,
                    companion_name = ?,
                    companion_tone = ?,
                    onboarded = ?,
                    updated_at = datetime('now')
                WHERE id = ?
                """,
                (new_owner, new_name, new_tone, 1 if new_on else 0, user_id),
            )
            await db.commit()
        return await self.get_user(user_id)

    async def create_session(self, user_id: int) -> str:
        token = secrets.token_urlsafe(32)
        expires = _now() + timedelta(days=SESSION_DAYS)
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
                (hash_session_token(token), user_id, _iso(expires)),
            )
            await db.commit()
        return token

    async def user_for_session(self, token: str) -> UserRow | None:
        if not token.strip():
            return None
        digest = hash_session_token(token.strip())
        now = _iso(_now())
        async with aiosqlite.connect(self._db_path) as db:
            cur = await db.execute(
                f"""
                SELECT {self._COLS}
                FROM users
                JOIN sessions ON sessions.user_id = users.id
                WHERE sessions.token_hash = ? AND sessions.expires_at > ?
                """,
                (digest, now),
            )
            row = await cur.fetchone()
            return self._row(row) if row else None

    async def delete_session(self, token: str) -> None:
        digest = hash_session_token(token.strip())
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("DELETE FROM sessions WHERE token_hash = ?", (digest,))
            await db.commit()
