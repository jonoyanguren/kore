"""Gmail reply helpers (D17)."""

from app.integrations.gmail.client import GmailMessageDetail, _extract_body_text, _strip_html
from app.integrations.gmail.oauth import build_authorize_url
from app.integrations.gmail.reply import reply_subject, reply_to_address
from app.integrations.gmail.tokens import scope_can_send, scope_has_gmail


def test_authorize_url_includes_send_scope():
    url = build_authorize_url(
        client_id="cid",
        redirect_uri="https://kore.fly.dev/api/gmail/callback",
        state="abc",
    )
    assert "gmail.modify" in url
    assert "gmail.send" in url


def test_scope_helpers():
    assert scope_has_gmail("https://www.googleapis.com/auth/gmail.modify")
    assert not scope_can_send("https://www.googleapis.com/auth/gmail.modify")
    assert scope_can_send("https://www.googleapis.com/auth/gmail.send")
    assert scope_can_send(
        "https://www.googleapis.com/auth/gmail.modify "
        "https://www.googleapis.com/auth/gmail.send"
    )


def test_reply_subject_adds_re():
    assert reply_subject("Hola") == "Re: Hola"
    assert reply_subject("Re: Hola") == "Re: Hola"
    assert reply_subject("RE: ya") == "RE: ya"


def test_reply_to_prefers_reply_to_header():
    msg = GmailMessageDetail(
        id="1",
        thread_id="t",
        subject="X",
        from_="Name <a@x.com>",
        snippet="",
        date="",
        unread=True,
        permalink="",
        reply_to="Desk <desk@x.com>",
    )
    assert reply_to_address(msg) == "desk@x.com"


def test_extract_plain_body():
    import base64

    plain = base64.urlsafe_b64encode(b"Hola mundo").decode("ascii").rstrip("=")
    payload = {
        "mimeType": "text/plain",
        "body": {"data": plain},
    }
    assert _extract_body_text(payload) == "Hola mundo"


def test_strip_html_basic():
    assert "hola" in _strip_html("<p>hola<br/>mundo</p>").lower()
