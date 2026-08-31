"""Chat/mission models from the paid plan. Internal slugs; never show USD caps."""

from __future__ import annotations

from typing import Any, Literal

from app.accounts.context import current_profile
from app.billing.access import billing_enforced
from app.config import settings

FLASH = "deepseek/deepseek-v4-flash"
PRO = "deepseek/deepseek-v4-pro"
_PRO_MODES = frozenset({"loco", "experto", "duro", "pro", "high", "calidad"})

Tier = Literal["cheap", "lite", "hybrid"]
_UNSET: Any = object()


def env_daily() -> str:
    return (settings.openrouter_model or "").strip() or PRO


def env_strong() -> str:
    return (settings.openrouter_model_strong or "").strip() or env_daily()


def _identity(
    plan: Any = _UNSET,
    legacy: Any = _UNSET,
) -> tuple[str | None, bool]:
    if plan is _UNSET or legacy is _UNSET:
        profile = current_profile.get()
        if profile is not None:
            if plan is _UNSET:
                plan = profile.billing_plan
            if legacy is _UNSET:
                legacy = profile.legacy_prompts
        else:
            if plan is _UNSET:
                plan = None
            if legacy is _UNSET:
                legacy = False
    pid = (plan or "").strip() or None
    if pid not in ("5", "10", "20"):
        pid = None
    return pid, bool(legacy)


def model_tier(*, plan: Any = _UNSET, legacy: Any = _UNSET) -> Tier:
    """5 = always Flash. 10 = Flash daily + Haiku strong. 20 / Jon / local = hybrid."""
    pid, is_legacy = _identity(plan, legacy)
    if is_legacy or not billing_enforced():
        return "hybrid"
    if pid == "20":
        return "hybrid"
    if pid == "10":
        return "lite"
    return "cheap"


def chat_model(*, strong: bool = False, plan: Any = _UNSET, legacy: Any = _UNSET) -> str:
    tier = model_tier(plan=plan, legacy=legacy)
    if tier == "cheap":
        return FLASH
    if strong:
        return env_strong()
    if tier == "lite":
        return FLASH
    return env_daily()


def mission_model(
    quality: str | None,
    *,
    plan: Any = _UNSET,
    legacy: Any = _UNSET,
) -> str:
    if model_tier(plan=plan, legacy=legacy) == "cheap":
        return FLASH
    q = (quality or "").strip().lower()
    if q in _PRO_MODES:
        return PRO
    return FLASH
