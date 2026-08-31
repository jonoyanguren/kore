"""Who may use the console vs who must pay. Webhooks own billing_status."""

from __future__ import annotations

from datetime import datetime, timezone

from app.accounts.store import UserRow
from app.config import settings

_SKIP_PREFIXES = (
    "/api/me",
    "/api/logout",
    "/api/billing",
)


def billing_enforced() -> bool:
    from app.billing.plans import stripe_price_id

    return bool(
        (settings.stripe_secret_key or "").strip() and stripe_price_id("5")
    )


def path_skips_billing(path: str) -> bool:
    p = path or ""
    return any(p == s or p.startswith(s + "/") for s in _SKIP_PREFIXES)


def _paid_until_ok(user: UserRow) -> bool:
    raw = (user.paid_until or "").strip()
    if not raw:
        return False
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt > datetime.now(timezone.utc)


def billing_ok(user: UserRow) -> bool:
    if user.legacy_prompts:
        return True
    if not billing_enforced():
        return True
    if not user.allowed:
        return False
    # past_due: keep access during dunning; cut on subscription.deleted.
    if (user.billing_status or "") in ("active", "past_due"):
        return True
    return _paid_until_ok(user)


def needs_paywall(user: UserRow) -> bool:
    return billing_enforced() and not billing_ok(user)
