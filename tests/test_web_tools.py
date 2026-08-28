"""Tests for web search/fetch helpers."""

from __future__ import annotations

from app.integrations.web.tools import _safe_http_url, _strip_html


def test_safe_http_url():
    assert _safe_http_url("https://example.com/a") == "https://example.com/a"
    assert _safe_http_url("http://foo.org") == "http://foo.org"
    assert _safe_http_url("ftp://x") is None
    assert _safe_http_url("https://localhost/x") is None
    assert _safe_http_url("https://127.0.0.1/") is None
    assert _safe_http_url("https://172.16.0.1/x") is None
    assert _safe_http_url("not a url") is None


def test_strip_html():
    assert _strip_html("<p>Hola <b>mundo</b></p>") == "Hola mundo"
    assert "&amp;" in _strip_html("a&amp;b") or "a&b" == _strip_html("a&amp;b")
