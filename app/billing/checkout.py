"""Stripe Checkout + Customer Portal. Keys stay on the server."""

from __future__ import annotations

import logging
import secrets

from fastapi import Request

from app.accounts.store import UserRow
from app.billing.plans import normalize_plan, stripe_price_id
from app.config import settings

logger = logging.getLogger(__name__)


def configured() -> bool:
    return bool(
        (settings.stripe_secret_key or "").strip() and stripe_price_id("5")
    )


def _client():
    from stripe import StripeClient

    key = (settings.stripe_secret_key or "").strip()
    if not key:
        raise RuntimeError("stripe not configured")
    return StripeClient(key)


def origin_from(request: Request) -> str:
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme
    host = (
        request.headers.get("x-forwarded-host")
        or request.headers.get("host")
        or request.url.netloc
    )
    if host:
        return f"{proto}://{host}".rstrip("/")
    return (settings.public_origin or "https://kore.fly.dev").rstrip("/")


async def create_checkout_session(
    user: UserRow, plan: str, request: Request
) -> str:
    """Return Checkout URL for monthly plan 5 | 10 | 20."""
    plan = normalize_plan(plan)
    price = stripe_price_id(plan)
    if not price:
        raise RuntimeError(f"plan {plan} price not configured")

    client = _client()
    origin = origin_from(request)
    ident = "korechk_" + secrets.token_hex(8)
    params: dict = {
        "mode": "subscription",
        "line_items": [{"price": price, "quantity": 1}],
        "success_url": origin + "/?billing=ok",
        "cancel_url": origin + "/?billing=cancel",
        "client_reference_id": str(user.id),
        "metadata": {"user_id": str(user.id), "plan": plan},
        "subscription_data": {
            "metadata": {"user_id": str(user.id), "plan": plan},
        },
    }
    if user.stripe_customer_id:
        params["customer"] = user.stripe_customer_id
    else:
        params["customer_email"] = user.email
    session = await client.v1.checkout.sessions.create_async(
        params,
        {"idempotency_key": ident},
    )
    url = getattr(session, "url", None)
    if not url:
        raise RuntimeError("checkout session missing url")
    return str(url)


async def create_portal_session(
    user: UserRow, request: Request, *, upgrade: bool = False
) -> str:
    if not user.stripe_customer_id:
        raise RuntimeError("no stripe customer")
    client = _client()
    origin = origin_from(request)
    params: dict = {
        "customer": user.stripe_customer_id,
        "return_url": origin + "/",
    }
    sub = (user.stripe_subscription_id or "").strip()
    if upgrade and sub:
        params["flow_data"] = {
            "type": "subscription_update",
            "subscription_update": {"subscription": sub},
        }
    try:
        session = await client.v1.billing_portal.sessions.create_async(params)
    except Exception:
        if "flow_data" not in params:
            raise
        logger.warning("stripe portal upgrade flow failed; opening portal home")
        params.pop("flow_data", None)
        session = await client.v1.billing_portal.sessions.create_async(params)
    url = getattr(session, "url", None)
    if not url:
        raise RuntimeError("portal session missing url")
    return str(url)
