"""Live LLM routing for console (Más drawer). Follows the user's paid plan."""

from __future__ import annotations

from typing import Any

from app.llm.plan_models import (
    FLASH,
    chat_model,
    mission_model,
    model_tier,
)

# Approximate OpenRouter list $/1M (in / out). Update when defaults change.
_PRICE: dict[str, tuple[str, str]] = {
    "deepseek/deepseek-v4-pro": ("$0.435", "$0.87"),
    "deepseek/deepseek-v4-flash": ("$0.09", "$0.18"),
    "anthropic/claude-haiku-4.5": ("$1", "$5"),
    "anthropic/claude-sonnet-4.6": ("$3", "$15"),
    "moonshotai/kimi-k2.5": ("$0.375", "$2.03"),
}

_UNSET: Any = object()


def _price(model: str) -> tuple[str, str]:
    return _PRICE.get(model.strip(), ("—", "—"))


def _row(role: str, model: str, uses: str) -> dict[str, str]:
    pin, pout = _price(model)
    return {
        "role": role,
        "model": model,
        "price_in": pin,
        "price_out": pout,
        "uses": uses,
    }


def llm_routing(*, plan: Any = _UNSET, legacy: Any = _UNSET) -> dict:
    kw = {}
    if plan is not _UNSET:
        kw["plan"] = plan
    if legacy is not _UNSET:
        kw["legacy"] = legacy
    tier = model_tier(**kw)
    daily = chat_model(strong=False, **kw)
    strong = chat_model(strong=True, **kw)
    mission_n = mission_model("normal", **kw)
    mission_p = mission_model("experto", **kw)

    if tier == "cheap":
        rows = [
            _row("Todo", FLASH, "Chat · Gmail · dream · misiones"),
        ]
        notes = [
            "Plan Entrar: todo en Flash, para que el mes dure.",
            "Precios ~$/1M tokens (lista OpenRouter).",
        ]
    elif tier == "lite":
        rows = [
            _row("Daily", daily, "Chat normal"),
            _row("Strong", strong, "Dream · Gmail · chat gordo"),
            _row("Misión Normal", mission_n, "Misiones modo Normal"),
            _row("Misión Pro", mission_p, "Misiones Loco / Experto / Duro"),
        ]
        notes = [
            "Plan Más: chat en Flash; Gmail y dream en Haiku.",
            "Precios ~$/1M tokens (lista OpenRouter).",
            "Modo de misión se elige al crear (Nueva): Normal, Loco, Experto, Duro.",
        ]
    else:
        rows = [
            _row("Daily", daily, "Chat normal"),
            _row("Strong", strong, "Dream · Gmail · chat gordo"),
            _row("Misión Normal", mission_n, "Misiones modo Normal"),
            _row("Misión Pro", mission_p, "Misiones Loco / Experto / Duro"),
        ]
        notes = [
            "Híbrido: chat en Pro; Gmail y dream en Haiku.",
            "Precios ~$/1M tokens (lista OpenRouter).",
            "Prompt cache en tool loops (session sticky).",
            "Modo de misión se elige al crear (Nueva): Normal, Loco, Experto, Duro.",
        ]

    return {"tier": tier, "rows": rows, "notes": notes}
