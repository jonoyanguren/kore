"""Minimal Telegram Bot API models for Phase 1.

Only the fields we actually read are declared. `extra="ignore"` on every
model means Telegram can add fields, send update types we don't model
(edited_message, callback_query, my_chat_member, ...), or include extra
message fields (photo, sticker, etc.) without ever causing a validation
error — those cases are simply invisible to us and handled as "no text"
in app/main.py.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class TelegramChat(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int


class TelegramUser(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    is_bot: bool = False
    first_name: str | None = None


class TelegramMessage(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    message_id: int
    chat: TelegramChat
    from_user: TelegramUser | None = Field(default=None, alias="from")
    text: str | None = None


class TelegramUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    update_id: int
    message: TelegramMessage | None = None
