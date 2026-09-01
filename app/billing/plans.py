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
        "blurb": "El mes contenido.",
        "use": "Uso diario, para el Día, un par de correos y un chat. Una misión, si entra.",
        "featured": False,
    },
    "10": {
        "id": "10",
        "eur": 10,
        "credit_usd": 2.0,
        "name": "Más",
        "blurb": "Lo mismo, con más mes.",
        "use": "Uso diario, para el Día, correo y chat cada día. Unas pocas misiones.",
        "featured": True,
    },
    "20": {
        "id": "20",
        "eur": 20,
        "credit_usd": 3.0,
        "name": "Holgado",
        "blurb": "Por si este mes aprietas.",
        "use": "Uso diario, para el Día, correo, chat y varias misiones.",
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


def next_plan(plan_id: str | None) -> str | None:
    """Next public plan, or None if already on 20 €."""
    p = (plan_id or "").strip()
    if p == "20":
        return None
    if p == "10":
        return "20"
    return "10"


def upgrade_offer(plan_id: str | None) -> dict[str, Any] | None:
    nxt = next_plan(plan_id)
    if nxt is None:
        return None
    row = _PLANS[nxt]
    return {"plan": nxt, "eur": row["eur"], "name": row["name"]}


def plan_from_price_id(price_id: str) -> str | None:
    raw = (price_id or "").strip()
    if not raw:
        return None
    for pid in PLAN_IDS:
        if stripe_price_id(pid) == raw:
            return pid
    return None
