"""Log of Gmail messages marked read (triage safety net)."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class MarkedReadEntry:
    at: float
    message_id: str
    subject: str
    from_: str
    permalink: str
    reason: str = "manual"  # manual | task | tool

    def as_dict(self) -> dict:
        d = asdict(self)
        d["from"] = d.pop("from_")
        return d


def marked_read_path_for_db(storage_db_path: str) -> Path:
    return Path(storage_db_path).resolve().parent / "gmail_marked_read.jsonl"


def append_marked_read(path: Path, entry: MarkedReadEntry) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(entry.as_dict(), ensure_ascii=False) + "\n"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line)
    try:
        path.chmod(0o600)
    except OSError:
        pass


def list_marked_read(
    path: Path,
    *,
    limit: int = 30,
    since: float | None = None,
) -> list[dict]:
    if not path.is_file():
        return []
    rows: list[dict] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        logger.exception("Failed reading marked-read log at %s", path)
        return []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            continue
        at = float(raw.get("at") or 0)
        if since is not None and at < since:
            continue
        rows.append(
            {
                "at": at,
                "message_id": str(raw.get("message_id") or ""),
                "subject": str(raw.get("subject") or "(sin asunto)"),
                "from": str(raw.get("from") or ""),
                "permalink": str(raw.get("permalink") or ""),
                "reason": str(raw.get("reason") or "manual"),
            }
        )
    rows.reverse()  # newest first
    return rows[: max(1, min(limit, 100))]


def today_madrid_start_unix() -> float:
    from app.timeutil import now_madrid

    n = now_madrid()
    start = n.replace(hour=0, minute=0, second=0, microsecond=0)
    return start.timestamp()
