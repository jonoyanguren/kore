"""Gmail OAuth helpers + token store."""

from __future__ import annotations

import tempfile
import time
from pathlib import Path

from app.integrations.gmail.oauth import (
    build_authorize_url,
    consume_oauth_state,
    create_oauth_state,
)
from app.integrations.gmail.tokens import (
    GMAIL_MODIFY_SCOPE,
    GmailTokenStore,
    GmailTokens,
    token_path_for_db,
)


def test_token_path_beside_db():
    assert token_path_for_db("/data/kore.db") == Path("/data/gmail_tokens.json")


def test_token_store_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        store = GmailTokenStore(Path(tmp) / "gmail_tokens.json")
        assert store.load() is None
        assert not store.connected()
        tokens = GmailTokens(
            access_token="a",
            refresh_token="r",
            expires_at=time.time() + 3600,
            email="jon@example.com",
            scope=GMAIL_MODIFY_SCOPE,
        )
        store.save(tokens)
        loaded = store.load()
        assert loaded is not None
        assert loaded.refresh_token == "r"
        assert loaded.email == "jon@example.com"
        assert loaded.access_valid()
        assert store.connected()
        store.clear()
        assert not store.connected()


def test_oauth_state_csrf():
    with tempfile.TemporaryDirectory() as tmp:
        db = str(Path(tmp) / "kore.db")
        state = create_oauth_state(db)
        assert consume_oauth_state(db, state)
        assert not consume_oauth_state(db, state)  # one-shot
        state = create_oauth_state(db)
        assert not consume_oauth_state(db, "wrong")
        # failed attempt consumes state file
        assert not consume_oauth_state(db, state)


def test_authorize_url_includes_modify_scope():
    url = build_authorize_url(
        client_id="cid",
        redirect_uri="https://kore.fly.dev/api/gmail/callback",
        state="abc",
    )
    assert "accounts.google.com" in url
    assert "gmail.modify" in url
    assert "access_type=offline" in url
    assert "prompt=consent" in url
    assert "state=abc" in url
