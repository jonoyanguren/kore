"""Speech-to-text via OpenRouter `/audio/transcriptions`."""

from __future__ import annotations

import base64
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

OPENROUTER_TRANSCRIBE_URL = "https://openrouter.ai/api/v1/audio/transcriptions"
MAX_AUDIO_BYTES = 12 * 1024 * 1024  # 12 MB

# Browser MediaRecorder → OpenRouter format slug
_MIME_TO_FORMAT: dict[str, str] = {
    "audio/webm": "webm",
    "audio/webm;codecs=opus": "webm",
    "audio/ogg": "ogg",
    "audio/ogg;codecs=opus": "ogg",
    "audio/mp4": "m4a",
    "audio/mpeg": "mp3",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/flac": "flac",
}


def audio_format_from_mime(mime: str | None) -> str:
    raw = (mime or "").strip().lower()
    if raw in _MIME_TO_FORMAT:
        return _MIME_TO_FORMAT[raw]
    base = raw.split(";")[0].strip()
    if base in _MIME_TO_FORMAT:
        return _MIME_TO_FORMAT[base]
    # Fallback: last subtype token (webm, ogg, …)
    if "/" in base:
        return base.rsplit("/", 1)[-1] or "webm"
    return "webm"


async def transcribe_audio(
    data: bytes,
    *,
    mime: str | None = None,
    language: str | None = None,
) -> str:
    """Return transcribed text. Raises ValueError / httpx.HTTPError on failure."""
    if not data:
        raise ValueError("audio vacío")
    if len(data) > MAX_AUDIO_BYTES:
        raise ValueError(f"audio demasiado grande (máx {MAX_AUDIO_BYTES // (1024 * 1024)} MB)")

    fmt = audio_format_from_mime(mime)
    lang = (language or settings.openrouter_stt_language or "").strip() or None
    payload: dict = {
        "model": settings.openrouter_stt_model,
        "input_audio": {
            "data": base64.b64encode(data).decode("ascii"),
            "format": fmt,
        },
    }
    if lang:
        payload["language"] = lang

    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://kore.fly.dev",
        "X-Title": "Kore",
    }
    async with httpx.AsyncClient(timeout=90.0) as client:
        res = await client.post(OPENROUTER_TRANSCRIBE_URL, headers=headers, json=payload)
        if res.status_code >= 400:
            detail = res.text[:400]
            logger.warning("transcribe failed %s: %s", res.status_code, detail)
            res.raise_for_status()
        body = res.json()
    text = (body.get("text") or "").strip()
    if not text:
        raise ValueError("transcripción vacía")
    return text
