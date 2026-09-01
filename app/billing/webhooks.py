"""Apply Stripe webhook events. Signature check lives in the HTTP layer.

Idempotent: each event id is claimed once in stripe_events. Kore does not poll
Stripe for billing state — these handlers are the source of truth.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.accounts.store import AccountStore, UserRow
from app.billing.plans import credit_usd, normalize_plan

logger = logging.getLogger(__name__)

HANDLED = frozenset(
    {
        "checkout.session.completed",
        "invoice.paid",
        "invoice.payment_failed",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    }
)


def _as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        data = to_dict()
        if isinstance(data, dict):
            return data
    return {}


def event_as_dict(event: Any) -> dict[str, Any]:
    data = _as_dict(event)
    if data.get("id") and data.get("type"):
        return data
    return {
        "id": getattr(event, "id", "") or "",
        "type": getattr(event, "type", "") or "",
        "data": {"object": _as_dict(getattr(getattr(event, "data", None), "object", None))},
    }


def _meta(obj: dict[str, Any]) -> dict[str, Any]:
    return _as_dict(obj.get("metadata"))


def _int_id(raw: Any) -> int | None:
    try:
        n = int(str(raw or "").strip())
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None


def _period_end_iso(obj: dict[str, Any]) -> str | None:
    end = obj.get("current_period_end") or obj.get("period_end")
    if not end:
        lines = _as_dict(obj.get("lines")).get("data") or []
        if lines:
            end = _as_dict(_as_dict(lines[0]).get("period")).get("end")
    if not end:
        return None
    try:
        return datetime.fromtimestamp(int(end), tz=timezone.utc).replace(
            microsecond=0
        ).isoformat()
    except (TypeError, ValueError, OSError):
        return None


def _llm_cap_for(user: UserRow, plan_id: str) -> float:
    """Keep operator-set unlimited (0) and owner accounts; else plan credit."""
    if user.legacy_prompts:
        return 0.0
    if user.llm_cap_usd is not None and float(user.llm_cap_usd) <= 0:
        return 0.0
    return credit_usd(plan_id)


def _map_sub_status(status: str) -> str:
    s = (status or "").strip().lower()
    if s in ("active", "trialing"):
        return "active"
    if s in ("past_due", "unpaid"):
        return "past_due"
    if s in ("canceled", "incomplete_expired"):
        return "canceled"
    return ""


async def _user_from_session(
    accounts: AccountStore, obj: dict[str, Any]
) -> UserRow | None:
    meta = _meta(obj)
    uid = _int_id(meta.get("user_id") or obj.get("client_reference_id"))
    if uid:
        user = await accounts.get_user(uid)
        if user is not None:
            return user
    customer = str(obj.get("customer") or "").strip()
    if customer:
        return await accounts.get_by_stripe_customer_id(customer)
    return None


async def _user_from_customer(
    accounts: AccountStore, obj: dict[str, Any]
) -> UserRow | None:
    meta = _meta(obj)
    uid = _int_id(meta.get("user_id"))
    if uid:
        user = await accounts.get_user(uid)
        if user is not None:
            return user
    customer = str(obj.get("customer") or "").strip()
    if customer:
        return await accounts.get_by_stripe_customer_id(customer)
    return None


async def _activate_sub(
    accounts: AccountStore,
    user: UserRow,
    *,
    customer_id: str,
    subscription_id: str,
    paid_until: str | None,
    plan: str | None,
) -> None:
    plan_id = normalize_plan(plan or user.billing_plan)
    await accounts.apply_billing(
        user.id,
        stripe_customer_id=customer_id or user.stripe_customer_id,
        stripe_subscription_id=subscription_id or user.stripe_subscription_id,
        billing_status="active",
        billing_plan=plan_id,
        llm_cap_usd=_llm_cap_for(user, plan_id),
        paid_until=paid_until or user.paid_until,
    )


async def apply_event(accounts: AccountStore, event: Any) -> str:
    """Apply one Stripe event. Returns ok | dup | ignored | no_user."""
    data = event_as_dict(event)
    eid = str(data.get("id") or "").strip()
    etype = str(data.get("type") or "").strip()
    if not eid or etype not in HANDLED:
        return "ignored"
    if not await accounts.claim_stripe_event(eid, etype):
        return "dup"
    obj = _as_dict(_as_dict(data.get("data")).get("object"))
    try:
        if etype == "checkout.session.completed":
            return await _on_checkout(accounts, obj)
        if etype == "invoice.paid":
            return await _on_invoice_paid(accounts, obj)
        if etype == "invoice.payment_failed":
            return await _on_invoice_failed(accounts, obj)
        if etype == "customer.subscription.updated":
            return await _on_sub_updated(accounts, obj)
        if etype == "customer.subscription.deleted":
            return await _on_sub_deleted(accounts, obj)
    except Exception:
        await accounts.release_stripe_event(eid)
        raise
    return "ignored"


async def _on_checkout(accounts: AccountStore, obj: dict[str, Any]) -> str:
    user = await _user_from_session(accounts, obj)
    if user is None:
        logger.warning("stripe checkout: no user for session %s", obj.get("id"))
        return "no_user"
    kind = str(_meta(obj).get("plan") or _meta(obj).get("kind") or "").strip().lower()
    mode = str(obj.get("mode") or "").strip().lower()
    customer = str(obj.get("customer") or "").strip()
    if mode == "payment" or kind == "pack":
        return "ignored"
    sub_id = str(obj.get("subscription") or "").strip()
    await _activate_sub(
        accounts,
        user,
        customer_id=customer,
        subscription_id=sub_id,
        paid_until=_period_end_iso(obj),
        plan=kind,
    )
    return "ok"


async def _on_invoice_paid(accounts: AccountStore, obj: dict[str, Any]) -> str:
    user = await _user_from_customer(accounts, obj)
    if user is None:
        return "no_user"
    reason = str(obj.get("billing_reason") or "").strip()
    customer = str(obj.get("customer") or "").strip()
    sub_id = str(obj.get("subscription") or "").strip()
    paid_until = _period_end_iso(obj)
    plan = str(_meta(obj).get("plan") or user.billing_plan or "")
    if reason == "subscription_cycle":
        plan_id = normalize_plan(plan)
        await accounts.apply_billing(
            user.id,
            stripe_customer_id=customer or user.stripe_customer_id,
            stripe_subscription_id=sub_id or user.stripe_subscription_id,
            billing_status="active",
            billing_plan=plan_id,
            llm_cap_usd=_llm_cap_for(user, plan_id),
            paid_until=paid_until,
        )
        return "ok"
    await _activate_sub(
        accounts,
        user,
        customer_id=customer,
        subscription_id=sub_id,
        paid_until=paid_until,
        plan=plan,
    )
    return "ok"


async def _on_invoice_failed(accounts: AccountStore, obj: dict[str, Any]) -> str:
    user = await _user_from_customer(accounts, obj)
    if user is None:
        return "no_user"
    await accounts.apply_billing(user.id, billing_status="past_due")
    return "ok"


async def _on_sub_updated(accounts: AccountStore, obj: dict[str, Any]) -> str:
    user = await _user_from_customer(accounts, obj)
    if user is None:
        return "no_user"
    mapped = _map_sub_status(str(obj.get("status") or ""))
    if not mapped:
        return "ignored"
    fields: dict[str, object] = {
        "billing_status": mapped,
        "stripe_customer_id": str(obj.get("customer") or "") or user.stripe_customer_id,
        "stripe_subscription_id": str(obj.get("id") or "") or user.stripe_subscription_id,
        "paid_until": _period_end_iso(obj) or user.paid_until,
    }
    await accounts.apply_billing(user.id, **fields)
    return "ok"


async def _on_sub_deleted(accounts: AccountStore, obj: dict[str, Any]) -> str:
    user = await _user_from_customer(accounts, obj)
    if user is None:
        return "no_user"
    await accounts.apply_billing(
        user.id,
        billing_status="canceled",
        stripe_subscription_id=None,
        paid_until=None,
    )
    return "ok"
