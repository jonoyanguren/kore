"""Persist Gmail OAuth tokens next to the SQLite DB (/data on Fly)."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

GMAIL_MODIFY_SCOPE = "https://www.googleapis.com/auth/gmail.modify"
GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"


def scope_has_gmail(scope: str) -> bool:
    low = (scope or "").lower()
    return "gmail.modify" in low or "gmail.readonly" in low or "mail.google.com" in low


def scope_can_send(scope: str) -> bool:
    low = (scope or "").lower()
    return "gmail.send" in low or "gmail.compose" in low or "mail.google.com" in low


def token_path_for_db(storage_db_path: str) -> Path:
    return Path(storage_db_path).resolve().parent / "gmail_tokens.json"


@dataclass
class GmailTokens:
    access_token: str
    refresh_token: str
    expires_at: float  # unix seconds
    token_type: str = "Bearer"
    scope: str = GMAIL_MODIFY_SCOPE
    email: str = ""

    def access_valid(self, skew_seconds: float = 60.0) -> bool:
        return bool(self.access_token) and time.time() < (self.expires_at - skew_seconds)


class GmailTokenStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> GmailTokens | None:
        if not self.path.is_file():
            return None
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            logger.exception("Failed reading Gmail tokens at %s", self.path)
            return None
        try:
            return GmailTokens(
                access_token=str(raw.get("access_token") or ""),
                refresh_token=str(raw.get("refresh_token") or ""),
                expires_at=float(raw.get("expires_at") or 0),
                token_type=str(raw.get("token_type") or "Bearer"),
                scope=str(raw.get("scope") or GMAIL_MODIFY_SCOPE),
                email=str(raw.get("email") or ""),
            )
        except (TypeError, ValueError):
            logger.exception("Invalid Gmail token payload at %s", self.path)
            return None

    def save(self, tokens: GmailTokens) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(asdict(tokens), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        tmp.replace(self.path)
        try:
            self.path.chmod(0o600)
        except OSError:
            pass

    def clear(self) -> None:
        if self.path.is_file():
            self.path.unlink()

    def connected(self) -> bool:
        tokens = self.load()
        return bool(tokens and tokens.refresh_token)
