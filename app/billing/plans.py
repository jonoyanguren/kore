"""Public plans: 5 / 10 / 20 €. Internal credits never leave this module."""

from __future__ import annotations

from typing import Any

from app.config import settings

PLAN_IDS = ("5", "10", "20")
DEFAULT_PLAN = "5"

# credit_usd is internal (OpenRouter). Never send to the client.
_PLANS: dict[str, dict[str, Any]] = {
    "5": {
        "id": "5",
        "eur": 5,
        "credit_usd": 1.0,
        "name": "Entrar",
        "blurb": "Día, correo y companion. El mes contenido.",
        "featured": False,
    },
    "10": {
        "id": "10",
        "eur": 10,
        "credit_usd": 2.0,
        "name": "Más",
        "blurb": "Lo mismo, con más mes por delante.",
        "featured": True,
    },
    "20": {
        "id": "20",
        "eur": 20,
        "credit_usd": 3.0,
        "name": "Holgado",
        "blurb": "Por si este mes lanzas de verdad.",
        "featured": False,
    },
}


def normalize_plan(raw: str | None) -> str:
    p = (raw or "").strip().lower().replace("plan_", "")
    if p in ("sub", "subscription"):
        return DEFAULT_PLAN
    return p if p in _PLANS else DEFAULT_PLAN


def credit_usd(plan_id: str | None) -> float:
    return float(_PLANS[normalize_plan(plan_id)]["credit_usd"])


def public_plans() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for pid in PLAN_IDS:
        row = {k: v for k, v in _PLANS[pid].items() if k != "credit_usd"}
        out.append(row)
    return out


def stripe_price_id(plan_id: str | None) -> str:
    pid = normalize_plan(plan_id)
    return (getattr(settings, f"stripe_price_{pid}", "") or "").strip()
