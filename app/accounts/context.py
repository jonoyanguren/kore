"""Request-scoped tenant: memory, vault, companion profile, Gmail tokens."""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.integrations.gmail.tokens import GmailTokenStore
    from app.storage.memory import MemoryStore
    from app.storage.vault import Vault


@dataclass(frozen=True)
class CompanionProfile:
    user_id: int
    email: str
    owner_name: str
    companion_name: str
    companion_tone: str
    legacy_prompts: bool
    onboarded: bool
    llm_cap_usd: float | None = None
    billing_plan: str | None = None


current_memory: ContextVar["MemoryStore | None"] = ContextVar(
    "kore_memory", default=None
)
current_vault: ContextVar["Vault | None"] = ContextVar("kore_vault", default=None)
current_profile: ContextVar[CompanionProfile | None] = ContextVar(
    "kore_profile", default=None
)
current_gmail_tokens: ContextVar["GmailTokenStore | None"] = ContextVar(
    "kore_gmail_tokens", default=None
)


def active_names() -> tuple[str, str]:
    from app.config import settings

    profile = current_profile.get()
    assistant = (
        profile.companion_name.strip()
        if profile and profile.companion_name.strip()
        else settings.assistant_name
    )
    owner = (
        profile.owner_name.strip()
        if profile and profile.owner_name.strip()
        else settings.owner_name
    )
    return assistant, owner


def personalize_prompt(text: str) -> str:
    assistant, owner = active_names()
    return text.replace("Jone", assistant).replace("Jon", owner)


def active_db_path(fallback: str) -> str:
    mem = current_memory.get()
    if mem is not None:
        return mem._db_path
    return fallback


def bind_tenant(
    *,
    memory: MemoryStore,
    vault: Vault,
    profile: CompanionProfile,
    gmail_tokens: GmailTokenStore | None = None,
) -> None:
    current_memory.set(memory)
    current_vault.set(vault)
    current_profile.set(profile)
    current_gmail_tokens.set(gmail_tokens)


def clear_tenant() -> None:
    current_memory.set(None)
    current_vault.set(None)
    current_profile.set(None)
    current_gmail_tokens.set(None)
