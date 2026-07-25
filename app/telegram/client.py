"""Thin wrapper over the Telegram Bot API — only what Phase 1 needs.

No conversation state, no polling, no command routing. Just:
- send a (possibly long) text reply, split to respect the 4096-char limit
- send a "typing..." chat action while we wait on Claude
"""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org"
SAFE_CHUNK_LEN = 4000  # Telegram's real limit is 4096; leave margin


def split_message(text: str, limit: int = SAFE_CHUNK_LEN) -> list[str]:
    """Split `text` into chunks under `limit`, preferring line/word boundaries."""
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    remaining = text
    while remaining:
        if len(remaining) <= limit:
            chunks.append(remaining)
            break
        split_at = remaining.rfind("\n", 0, limit)
        if split_at == -1:
            split_at = remaining.rfind(" ", 0, limit)
        if split_at == -1:
            split_at = limit
        chunks.append(remaining[:split_at])
        remaining = remaining[split_at:].lstrip()
    return chunks


class TelegramClient:
    def __init__(self, bot_token: str, http_client: httpx.AsyncClient) -> None:
        self._base_url = f"{TELEGRAM_API_BASE}/bot{bot_token}"
        self._http = http_client

    async def send_message(self, chat_id: int, text: str) -> None:
        """Send `text` to `chat_id`, splitting into multiple messages if needed.

        Chunks are sent sequentially (awaited one at a time) so they arrive
        in reading order — Telegram doesn't guarantee ordering for
        concurrently-fired sendMessage calls.
        """
        for chunk in split_message(text):
            await self._post("sendMessage", {"chat_id": chat_id, "text": chunk})

    async def send_typing(self, chat_id: int) -> None:
        await self._post("sendChatAction", {"chat_id": chat_id, "action": "typing"})

    async def set_webhook(self, url: str, secret_token: str) -> dict:
        response = await self._http.post(
            f"{self._base_url}/setWebhook",
            data={"url": url, "secret_token": secret_token},
        )
        response.raise_for_status()
        return response.json()

    async def get_webhook_info(self) -> dict:
        response = await self._http.get(f"{self._base_url}/getWebhookInfo")
        response.raise_for_status()
        return response.json()

    async def _post(self, method: str, data: dict) -> None:
        try:
            response = await self._http.post(f"{self._base_url}/{method}", data=data)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error(
                "Telegram API error on %s: %s - %s", method, e.response.status_code, e.response.text
            )
        except httpx.HTTPError:
            logger.exception("Telegram API request failed on %s", method)
