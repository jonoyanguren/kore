"""Email → task proposal fallback (no LLM)."""

from app.integrations.gmail.client import GmailMessage
from app.integrations.gmail.to_task import _fallback_proposal


def test_fallback_strips_re_prefix():
    msg = GmailMessage(
        id="1",
        thread_id="t",
        subject="Re: Factura julio",
        from_="Esteve <e@x.com>",
        snippet="Adjunto factura",
        date="2026-07-28",
        unread=True,
        permalink="https://mail.google.com/mail/u/0/#inbox/1",
    )
    p = _fallback_proposal(msg)
    assert p["title"] == "Factura julio"
    assert "Esteve" in (p["notes"] or "")
