"""Gmail digest helpers (no LLM)."""

from __future__ import annotations

import time
from pathlib import Path

from app.integrations.gmail.digest import (
    InboxDigest,
    _parse_bullets,
    cached_digest_for,
    save_digest,
)


def test_parse_bullets():
    text = """
- Factura de Vodafone: revisar antes del viernes
* Newsletter de Product Hunt (ruido)
1. Cita con Andrea confirmada el jueves
"""
    bullets = _parse_bullets(text)
    assert len(bullets) == 3
    assert "Vodafone" in bullets[0]


def test_digest_cache_fingerprint(tmp_path: Path):
    path = tmp_path / "gmail_digest.json"
    digest = InboxDigest(
        bullets=["Algo importante"],
        message_ids=["a", "b"],
        created_at=time.time(),
        email="jon@example.com",
    )
    save_digest(path, digest)
    assert cached_digest_for(path, ["b", "a"]) is not None
    assert cached_digest_for(path, ["a", "c"]) is None
    stale = InboxDigest(
        bullets=["viejo"],
        message_ids=["a", "b"],
        created_at=time.time() - 10_000,
    )
    save_digest(path, stale)
    assert cached_digest_for(path, ["a", "b"], ttl=60) is None
