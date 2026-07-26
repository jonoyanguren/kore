"""Minimal Telegram Bot API models for the companion webhook."""

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


class TelegramPhotoSize(BaseModel):
    model_config = ConfigDict(extra="ignore")

    file_id: str
    file_unique_id: str | None = None
    width: int | None = None
    height: int | None = None
    file_size: int | None = None


class TelegramMessage(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    message_id: int
    chat: TelegramChat
    from_user: TelegramUser | None = Field(default=None, alias="from")
    text: str | None = None
    caption: str | None = None
    photo: list[TelegramPhotoSize] | None = None


class TelegramUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    update_id: int
    message: TelegramMessage | None = None
