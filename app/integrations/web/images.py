"""Page image extraction + same-origin proxy fetch (SSRF-safe)."""

from __future__ import annotations

import ipaddress
import logging
import re
import socket
from dataclasses import dataclass
from html import unescape
from urllib.parse import urljoin, urlparse

import httpx

logger = logging.getLogger(__name__)

USER_AGENT = "KoreCompanion/1.0 (+https://kore.fly.dev; personal assistant)"

MAX_IMAGE_BYTES = 4_000_000
MAX_REDIRECTS = 5
MAX_PAGE_IMAGES = 8

_ALLOWED_TYPES = frozenset(
    {
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/gif",
        "image/webp",
        "image/avif",
    }
)

_OG_RE = re.compile(
    r"<meta\b[^>]*>",
    re.I,
)
_META_PROP_RE = re.compile(
    r"""(?:property|name)\s*=\s*["']([^"']+)["']""",
    re.I,
)
_META_CONTENT_RE = re.compile(
    r"""content\s*=\s*["']([^"']+)["']""",
    re.I,
)
_IMG_SRC_RE = re.compile(
    r"""<img\b[^>]*?\bsrc\s*=\s*["']([^"']+)["']""",
    re.I | re.S,
)
_IMG_EXT_RE = re.compile(r"\.(?:jpe?g|png|gif|webp|avif)(?:\?|#|$)", re.I)


@dataclass(frozen=True)
class FetchedImage:
    body: bytes
    content_type: str


def public_http_url(url: str) -> str | None:
    """Allow only http(s) to a non-local host. No DNS."""
    u = (url or "").strip()
    if not u or u.startswith("data:") or u.startswith("javascript:"):
        return None
    parsed = urlparse(u)
    if parsed.scheme not in ("http", "https"):
        return None
    host = (parsed.hostname or "").strip().lower().rstrip(".")
    if not host or parsed.username or parsed.password:
        return None
    if _host_blocked_static(host):
        return None
    return u


def _host_blocked_static(host: str) -> bool:
    if host in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
        return True
    if host.endswith(".localhost") or host.endswith(".local") or host.endswith(".internal"):
        return True
    if "metadata.google.internal" in host:
        return True
    try:
        ip = ipaddress.ip_address(host)
        return not ip.is_global
    except ValueError:
        pass
    parts = host.split(".")
    if len(parts) == 4 and all(p.isdigit() for p in parts):
        try:
            ip = ipaddress.ip_address(host)
            return not ip.is_global
        except ValueError:
            return True
    if parts[0] == "10":
        return True
    if parts[0] == "192" and len(parts) > 1 and parts[1] == "168":
        return True
    if parts[0] == "169" and len(parts) > 1 and parts[1] == "254":
        return True
    if parts[0] == "172" and len(parts) > 1 and parts[1].isdigit():
        n = int(parts[1])
        if 16 <= n <= 31:
            return True
    return False


def host_resolves_public(host: str) -> bool:
    h = (host or "").strip().lower().rstrip(".")
    if not h or _host_blocked_static(h):
        return False
    try:
        ipaddress.ip_address(h)
        return True
    except ValueError:
        pass
    try:
        infos = socket.getaddrinfo(h, None, type=socket.SOCK_STREAM)
    except OSError:
        return False
    if not infos:
        return False
    for info in infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            return False
        if not ip.is_global:
            return False
    return True


def extract_page_images(html: str, page_url: str) -> list[str]:
    """og:image / twitter:image first, then a few <img> with image extensions."""
    if not html:
        return []
    seen: set[str] = set()
    out: list[str] = []

    def add(raw: str) -> None:
        if len(out) >= MAX_PAGE_IMAGES:
            return
        href = unescape((raw or "").strip())
        if not href:
            return
        abs_url = urljoin(page_url, href)
        safe = public_http_url(abs_url)
        if not safe or safe in seen:
            return
        seen.add(safe)
        out.append(safe)

    for tag in _OG_RE.findall(html):
        prop_m = _META_PROP_RE.search(tag)
        content_m = _META_CONTENT_RE.search(tag)
        if not prop_m or not content_m:
            continue
        prop = prop_m.group(1).strip().lower()
        if prop in ("og:image", "og:image:url", "twitter:image", "twitter:image:src"):
            add(content_m.group(1))

    for m in _IMG_SRC_RE.finditer(html):
        src = unescape(m.group(1).strip())
        if not _IMG_EXT_RE.search(src.split("?")[0]):
            continue
        add(src)

    return out


def _content_type_ok(header: str) -> str | None:
    ctype = (header or "").split(";")[0].strip().lower()
    if ctype in _ALLOWED_TYPES:
        return "image/jpeg" if ctype == "image/jpg" else ctype
    return None


def _sniff_image_type(body: bytes) -> str | None:
    if len(body) < 12:
        return None
    if body[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if body[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if body[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if body[:4] == b"RIFF" and body[8:12] == b"WEBP":
        return "image/webp"
    if body[4:8] == b"ftyp" and body[8:12] in (b"avif", b"avis"):
        return "image/avif"
    return None


async def fetch_public_image(
    url: str,
    *,
    client: httpx.AsyncClient | None = None,
    check_dns: bool | None = None,
) -> FetchedImage | None:
    """GET a public image. `client` injected in tests (skips DNS unless check_dns=True)."""
    resolve = check_dns if check_dns is not None else client is None
    own_client = client is None
    if own_client:
        client = httpx.AsyncClient(
            timeout=20.0,
            follow_redirects=False,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
            },
        )
    assert client is not None
    try:
        return await _fetch_hops(url, client=client, resolve=resolve)
    except Exception as e:
        logger.info("image proxy failed %s: %s", url[:120], e)
        return None
    finally:
        if own_client:
            await client.aclose()


async def _fetch_hops(
    url: str,
    *,
    client: httpx.AsyncClient,
    resolve: bool,
) -> FetchedImage | None:
    current = public_http_url(url)
    if not current:
        return None
    for _ in range(MAX_REDIRECTS):
        host = urlparse(current).hostname or ""
        if resolve and not host_resolves_public(host):
            return None
        parsed = urlparse(current)
        res = await client.get(
            current,
            headers={"Referer": f"{parsed.scheme}://{parsed.netloc}/"},
        )
        if res.status_code in (301, 302, 303, 307, 308):
            loc = (res.headers.get("location") or "").strip()
            if not loc:
                return None
            nxt = public_http_url(urljoin(current, loc))
            if not nxt:
                return None
            current = nxt
            continue
        if res.status_code != 200:
            return None
        body = res.content
        if not body or len(body) > MAX_IMAGE_BYTES:
            return None
        sniffed = _sniff_image_type(body)
        header_type = _content_type_ok(res.headers.get("content-type") or "")
        content_type = sniffed or header_type
        if content_type is None:
            return None
        return FetchedImage(body=body, content_type=content_type)
    return None
