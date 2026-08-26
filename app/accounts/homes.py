"""Per-user Kore home: isolated SQLite + vault. Shared accounts DB stays out."""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

from app.accounts.context import bind_tenant
from app.accounts.store import AccountStore, UserRow
from app.config import settings
from app.integrations.gmail.tokens import GmailTokenStore
from app.storage.memory import MemoryStore
from app.storage.vault import Vault

logger = logging.getLogger(__name__)


def data_root() -> Path:
    return Path(settings.storage_db_path).resolve().parent


def accounts_db_path() -> Path:
    return data_root() / "accounts.db"


def home_dir(user_id: int) -> Path:
    return data_root() / "users" / str(user_id)


@dataclass
class TenantHome:
    user_id: int
    memory: MemoryStore
    vault: Vault
    gmail_tokens: GmailTokenStore

    @property
    def db_path(self) -> Path:
        return Path(self.memory._db_path)


class Homes:
    def __init__(self, accounts: AccountStore) -> None:
        self.accounts = accounts
        self._cache: dict[int, TenantHome] = {}

    async def open(self, user_id: int) -> TenantHome:
        cached = self._cache.get(user_id)
        if cached is not None:
            return cached
        root = home_dir(user_id)
        root.mkdir(parents=True, exist_ok=True)
        db = root / "kore.db"
        memory = MemoryStore(str(db))
        await memory.init()
        vault = Vault(root / "vault")
        vault.ensure()
        tokens = GmailTokenStore(root / "gmail_tokens.json")
        home = TenantHome(
            user_id=user_id,
            memory=memory,
            vault=vault,
            gmail_tokens=tokens,
        )
        self._cache[user_id] = home
        return home

    async def all_open(self) -> list[TenantHome]:
        homes: list[TenantHome] = []
        for uid in await self.accounts.list_user_ids():
            homes.append(await self.open(uid))
        return homes

    async def bootstrap_legacy(self) -> UserRow | None:
        """First boot: create Jon's account and move /data/kore.db into users/{id}/."""
        existing = await self.accounts.legacy_user()
        if existing is not None:
            return existing
        if await self.accounts.count_users() > 0:
            return None
        secret = (settings.console_secret or "").strip()
        if len(secret) < 8:
            logger.info("No bootstrap user — CONSOLE_SECRET missing or short")
            return None
        email = (settings.owner_email or "jon@kore.local").strip().lower()
        user = await self.accounts.create_user(
            email=email,
            password=secret,
            owner_name=settings.owner_name,
            companion_name=settings.assistant_name,
            companion_tone="",
            legacy_prompts=True,
            onboarded=True,
        )
        await self._migrate_legacy_files(user.id)
        logger.info("Bootstrap user id=%s email=%s (legacy home)", user.id, email)
        return user

    async def _migrate_legacy_files(self, user_id: int) -> None:
        dest = home_dir(user_id)
        dest.mkdir(parents=True, exist_ok=True)
        dest_db = dest / "kore.db"
        dest_vault = dest / "vault"
        dest_tokens = dest / "gmail_tokens.json"

        src_db = Path(settings.storage_db_path).resolve()
        old_tokens = src_db.parent / "gmail_tokens.json"
        src_vault = Path(settings.resolved_vault_root()).resolve()

        if src_db.is_file() and src_db != dest_db.resolve():
            if dest_db.exists():
                dest_db.unlink()
            shutil.move(str(src_db), str(dest_db))
            logger.info("Moved legacy DB %s → %s", src_db, dest_db)
            for suffix in ("-wal", "-shm"):
                side = Path(str(src_db) + suffix)
                if side.is_file():
                    shutil.move(str(side), str(dest_db) + suffix)

        if src_vault.is_dir() and src_vault != dest_vault.resolve():
            if dest_vault.exists():
                shutil.rmtree(dest_vault)
            shutil.move(str(src_vault), str(dest_vault))
            logger.info("Moved legacy vault %s → %s", src_vault, dest_vault)

        if old_tokens.is_file() and old_tokens.resolve() != dest_tokens.resolve():
            shutil.move(str(old_tokens), str(dest_tokens))
            logger.info("Moved Gmail tokens → %s", dest_tokens)

        for name in ("gmail_marked_read.jsonl", "gmail_digest.json"):
            src = src_db.parent / name
            dest_file = dest / name
            if src.is_file() and src.resolve() != dest_file.resolve():
                shutil.move(str(src), str(dest_file))
                logger.info("Moved %s → %s", name, dest_file)


def bind_tenant_home(home: TenantHome, user: UserRow) -> None:
    bind_tenant(
        memory=home.memory,
        vault=home.vault,
        profile=user.profile(),
        gmail_tokens=home.gmail_tokens,
    )
