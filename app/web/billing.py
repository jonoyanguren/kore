"""Billing HTTP: Checkout, Customer Portal, Stripe webhooks."""

from __future__ import annotations

import logging
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from app.billing.access import billing_enforced, needs_paywall
from app.billing.checkout import configured as stripe_configured
from app.billing.checkout import create_checkout_session, create_portal_session
from app.billing.plans import public_plans
from app.config import settings
from app.web.auth import accounts_of, require_console_auth

logger = logging.getLogger(__name__)

router = APIRouter(tags=["billing"])


class CheckoutBody(BaseModel):
    kind: Literal["5", "10", "20"] = "5"


def public_pricing() -> dict[str, Any]:
    return {
        "plans": public_plans(),
        "enforced": billing_enforced(),
    }


def billing_public(user) -> dict[str, Any]:
    needed = needs_paywall(user)
    return {
        "needed": needed,
        "status": user.billing_status or "none",
        "plan": user.billing_plan,
        "enforced": billing_enforced(),
        "plans": public_plans(),
        "has_customer": bool(user.stripe_customer_id),
        "legacy": bool(user.legacy_prompts),
    }


@router.post("/billing/checkout", dependencies=[Depends(require_console_auth)])
async def billing_checkout(request: Request, body: CheckoutBody) -> dict[str, Any]:
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="unauthorized")
    if not stripe_configured():
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, detail="stripe_not_configured"
        )
    try:
        url = await create_checkout_session(user, body.kind, request)
    except RuntimeError as exc:
        logger.warning("checkout failed: %s", exc)
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, detail="stripe_not_configured"
        ) from exc
    except Exception:
        logger.exception("stripe checkout error")
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, detail="stripe_error"
        ) from None
    return {"ok": True, "url": url}


@router.post("/billing/portal", dependencies=[Depends(require_console_auth)])
async def billing_portal(request: Request) -> dict[str, Any]:
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="unauthorized")
    if not stripe_configured() or not user.stripe_customer_id:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="no_stripe_customer"
        )
    try:
        url = await create_portal_session(user, request)
    except Exception:
        logger.exception("stripe portal error")
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, detail="stripe_error"
        ) from None
    return {"ok": True, "url": url}


@router.post("/stripe/webhook")
async def stripe_webhook(request: Request) -> dict[str, Any]:
    accounts = accounts_of(request)
    if accounts is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="accounts not ready")
    secret = (settings.stripe_webhook_secret or "").strip()
    key = (settings.stripe_secret_key or "").strip()
    if not secret or not key:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, detail="stripe_not_configured"
        )
    payload = await request.body()
    sig = request.headers.get("stripe-signature") or ""
    from stripe import StripeClient
    from stripe import SignatureVerificationError

    client = StripeClient(key)
    try:
        event = client.construct_event(payload, sig, secret)
    except (SignatureVerificationError, ValueError):
        logger.warning("stripe webhook: bad signature")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="invalid_signature") from None
    from app.billing.webhooks import apply_event

    result = await apply_event(accounts, event)
    logger.info(
        "stripe webhook %s type=%s result=%s",
        getattr(event, "id", ""),
        getattr(event, "type", ""),
        result,
    )
    return {"ok": True, "result": result}
