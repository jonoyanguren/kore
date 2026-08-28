"""Image extraction + SSRF-safe proxy fetch."""

from __future__ import annotations

import asyncio

import httpx

from app.integrations.web.images import (
    extract_page_images,
    fetch_public_image,
    public_http_url,
)
from app.integrations.web.tools import _safe_http_url

JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + b"\x00" * 24


def test_public_http_url_blocks_private():
    assert public_http_url("https://example.com/a") == "https://example.com/a"
    assert _safe_http_url("http://foo.org") == "http://foo.org"
    assert public_http_url("ftp://x") is None
    assert public_http_url("https://localhost/x") is None
    assert public_http_url("https://127.0.0.1/") is None
    assert public_http_url("https://172.16.1.9/img.jpg") is None
    assert public_http_url("https://192.168.0.2/x") is None
    assert public_http_url("https://user:pass@example.com/x") is None
    assert public_http_url("not a url") is None


def test_extract_page_images():
    html = """
    <html><head>
    <meta property="og:image" content="https://cdn.example.com/hero.jpg">
    <meta name="twitter:image" content="https://cdn.example.com/tw.png">
    </head><body>
    <img src="/photos/a.webp">
    <img src="https://cdn.example.com/logo.svg">
    <img src="https://cdn.example.com/photo.jpeg?w=800">
    </body></html>
    """
    urls = extract_page_images(html, "https://shop.example.com/item")
    assert urls[0] == "https://cdn.example.com/hero.jpg"
    assert "https://cdn.example.com/tw.png" in urls
    assert "https://shop.example.com/photos/a.webp" in urls
    assert "https://cdn.example.com/photo.jpeg?w=800" in urls
    assert not any(u.endswith(".svg") for u in urls)


def test_extract_og_reverse_attrs():
    html = '<meta content="https://cdn.example.com/x.jpg" property="og:image">'
    urls = extract_page_images(html, "https://example.com/")
    assert urls == ["https://cdn.example.com/x.jpg"]


async def _fetch_cases() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url == "https://cdn.example.com/ok.jpg":
            return httpx.Response(
                200, content=JPEG, headers={"content-type": "image/jpeg"}
            )
        if url.startswith("https://cdn.example.com/redir"):
            return httpx.Response(302, headers={"location": "http://127.0.0.1/secret"})
        if url.endswith("/html"):
            return httpx.Response(
                200,
                content=b"<html>nope</html>",
                headers={"content-type": "text/html"},
            )
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        ok = await fetch_public_image(
            "https://cdn.example.com/ok.jpg", client=client
        )
        assert ok is not None
        assert ok.content_type == "image/jpeg"
        assert ok.body[:3] == b"\xff\xd8\xff"

        assert (
            await fetch_public_image("http://127.0.0.1/x.png", client=client)
            is None
        )
        assert (
            await fetch_public_image(
                "https://cdn.example.com/redir", client=client
            )
            is None
        )
        assert (
            await fetch_public_image(
                "https://cdn.example.com/html", client=client
            )
            is None
        )
        assert (
            await fetch_public_image(
                "https://cdn.example.com/missing.jpg", client=client
            )
            is None
        )


def test_fetch_public_image_ssrf_and_types():
    asyncio.run(_fetch_cases())
