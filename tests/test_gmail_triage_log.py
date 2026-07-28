"""Triage marked-read log."""

from __future__ import annotations

import time
from pathlib import Path

from app.integrations.gmail.triage_log import (
    MarkedReadEntry,
    append_marked_read,
    list_marked_read,
)


def test_append_and_list_newest_first(tmp_path: Path):
    path = tmp_path / "gmail_marked_read.jsonl"
    append_marked_read(
        path,
        MarkedReadEntry(
            at=100.0,
            message_id="a",
            subject="Old",
            from_="a@x.com",
            permalink="https://mail/a",
            reason="manual",
        ),
    )
    append_marked_read(
        path,
        MarkedReadEntry(
            at=200.0,
            message_id="b",
            subject="New",
            from_="b@x.com",
            permalink="https://mail/b",
            reason="task",
        ),
    )
    rows = list_marked_read(path, limit=10)
    assert len(rows) == 2
    assert rows[0]["message_id"] == "b"
    assert rows[0]["reason"] == "task"
    assert rows[1]["subject"] == "Old"


def test_list_since_filter(tmp_path: Path):
    path = tmp_path / "gmail_marked_read.jsonl"
    now = time.time()
    append_marked_read(
        path,
        MarkedReadEntry(
            at=now - 10_000,
            message_id="old",
            subject="Yesterday",
            from_="x",
            permalink="",
        ),
    )
    append_marked_read(
        path,
        MarkedReadEntry(
            at=now,
            message_id="new",
            subject="Today",
            from_="y",
            permalink="",
        ),
    )
    rows = list_marked_read(path, limit=10, since=now - 60)
    assert len(rows) == 1
    assert rows[0]["message_id"] == "new"
