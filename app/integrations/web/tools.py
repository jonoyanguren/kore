"""Web access tools: search + fetch page text (httpx, no extra API keys)."""

from __future__ import annotations

import html as html_lib
import logging
import re
from typing import Any, Awaitable, Callable
from urllib.parse import quote_plus, urlparse

import httpx

logger = logging.getLogger(__name__)

ToolHandler = Callable[[dict[str, Any]], Awaitable[str]]

MAX_FETCH_CHARS = 12_000
MAX_SEARCH_RESULTS = 6
USER_AGENT = "KoreCompanion/1.0 (+https://kore.fly.dev; personal assistant)"

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_RESULT_RE = re.compile(
    r'uddg=([^&"]+).*?class="result__a"[^>]*>(.*?)</a>.*?class="result__snippet"[^>]*>(.*?)</(?:a|td)',
    re.I | re.S,
)
_RESULT_RE_ALT = re.compile(
    r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
    re.I | re.S,
)


def _strip_html(raw: str) -> str:
    text = _TAG_RE.sub(" ", raw)
    text = html_lib.unescape(text)
    return _WS_RE.sub(" ", text).strip()


def _safe_http_url(url: str) -> str | None:
    u = (url or "").strip()
    if not u:
        return None
    parsed = urlparse(u)
    if parsed.scheme not in ("http", "https"):
        return None
    if not parsed.netloc:
        return None
    # Block obvious local/metadata targets
    host = parsed.hostname or ""
    if host in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
        return None
    if host.startswith("10.") or host.startswith("192.168.") or host.startswith("169.254."):
        return None
    return u


async def _ddg_search(query: str, *, limit: int) -> list[dict[str, str]]:
    """Parse DuckDuckGo HTML results (no API key)."""
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    async with httpx.AsyncClient(
        timeout=20.0,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    ) as client:
        res = await client.get(url)
        res.raise_for_status()
        body = res.text

    results: list[dict[str, str]] = []
    for m in _RESULT_RE_ALT.finditer(body):
        href = html_lib.unescape(m.group(1))
        title = _strip_html(m.group(2))
        if not title:
            continue
        # DDG wraps redirects sometimes
        if "uddg=" in href:
            from urllib.parse import parse_qs, unquote, urlparse as up

            qs = parse_qs(up(href).query)
            if "uddg" in qs:
                href = unquote(qs["uddg"][0])
        if not href.startswith("http"):
            continue
        results.append({"title": title, "url": href, "snippet": ""})
        if len(results) >= limit:
            break

    # Snippets: lighter second pass
    snippets = re.findall(
        r'class="result__snippet"[^>]*>(.*?)</(?:a|td|div)',
        body,
        flags=re.I | re.S,
    )
    for i, snip in enumerate(snippets):
        if i < len(results):
            results[i]["snippet"] = _strip_html(snip)[:280]

    return results


def build_web_tools() -> tuple[list[dict], dict[str, ToolHandler]]:
    async def _web_search(args: dict[str, Any]) -> str:
        query = (args.get("query") or "").strip()
        if not query:
            return "Falta query."
        limit = min(max(int(args.get("limit") or MAX_SEARCH_RESULTS), 1), 10)
        try:
            rows = await _ddg_search(query, limit=limit)
        except Exception as e:
            logger.warning("web_search failed: %s", e)
            return f"No pude buscar ahora ({e})."
        if not rows:
            return f"Sin resultados para: {query}"
        lines = [f"Resultados para «{query}»:"]
        for i, r in enumerate(rows, 1):
            lines.append(f"{i}. {r['title']}")
            if r.get("snippet"):
                lines.append(f"   {r['snippet']}")
            lines.append(f"   {r['url']}")
        return "\n".join(lines)

    async def _fetch_url(args: dict[str, Any]) -> str:
        raw = (args.get("url") or "").strip()
        url = _safe_http_url(raw)
        if not url:
            return "URL inválida (solo http/https públicos)."
        try:
            async with httpx.AsyncClient(
                timeout=25.0,
                follow_redirects=True,
                headers={"User-Agent": USER_AGENT},
            ) as client:
                res = await client.get(url)
                res.raise_for_status()
                ctype = (res.headers.get("content-type") or "").lower()
                if "html" in ctype or "text/" in ctype or not ctype:
                    text = _strip_html(res.text)
                else:
                    return f"Tipo no texto ({ctype}); no leo binarios."
        except Exception as e:
            logger.warning("fetch_url failed %s: %s", url, e)
            return f"No pude abrir {url} ({e})."
        if not text:
            return f"Página vacía: {url}"
        if len(text) > MAX_FETCH_CHARS:
            text = text[:MAX_FETCH_CHARS] + "\n…[truncado]"
        return f"Contenido de {url}:\n\n{text}"

    schemas: list[dict] = [
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": (
                    "Buscar en internet (resultados actuales). Úsalo cuando Jon "
                    "pida datos del mundo real, noticias, docs externas, o algo "
                    "que no esté en memoria/vault."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Consulta de búsqueda",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Máx resultados (default 6)",
                        },
                    },
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "fetch_url",
                "description": (
                    "Abrir una URL http(s) y devolver el texto de la página. "
                    "Útil tras web_search o si Jon pega un link."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL completa"},
                    },
                    "required": ["url"],
                },
            },
        },
    ]
    handlers: dict[str, ToolHandler] = {
        "web_search": _web_search,
        "fetch_url": _fetch_url,
    }
    return schemas, handlers
