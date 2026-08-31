"""Stripe billing: webhooks are the source of truth (no polling)."""

from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from stripe import WebhookSignature

from app.accounts.homes import Homes
from app.accounts.store import AccountStore
from app.billing.access import billing_ok
from app.billing.webhooks import apply_event
from app.config import settings
from app.web.api import router as console_api_router


def _evt(eid: str, etype: str, obj: dict) -> dict:
    return {
        "id": eid,
        "object": "event",
        "type": etype,
        "data": {"object": obj},
    }


async def _store() -> tuple[AccountStore, object]:
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    accounts = AccountStore(str(root / "accounts.db"))
    await accounts.init()
    user = await accounts.create_user(
        email="ana@example.com",
        password="password1",
        owner_name="Ana",
    )
    return accounts, user, tmp


def test_checkout_webhook_activates_and_is_idempotent():
    async def _run() -> None:
        accounts, user, tmp = await _store()
        try:
            first = await apply_event(
                accounts,
                _evt(
                    "evt_sub_1",
                    "checkout.session.completed",
                    {
                        "id": "cs_1",
                        "mode": "subscription",
                        "customer": "cus_1",
                        "subscription": "sub_1",
                        "client_reference_id": str(user.id),
                        "metadata": {"user_id": str(user.id), "kind": "sub"},
                    },
                ),
            )
            assert first == "ok"
            got = await accounts.get_user(user.id)
            assert got is not None
            assert got.billing_status == "active"
            assert got.stripe_customer_id == "cus_1"
            assert got.stripe_subscription_id == "sub_1"
            assert got.llm_cap_usd == 1.0
            assert got.billing_plan == "5"
            assert billing_ok(got)

            dup = await apply_event(
                accounts,
                _evt(
                    "evt_sub_1",
                    "checkout.session.completed",
                    {
                        "id": "cs_1",
                        "mode": "subscription",
                        "customer": "cus_1",
                        "client_reference_id": str(user.id),
                    },
                ),
            )
            assert dup == "dup"
        finally:
            tmp.cleanup()

    asyncio.run(_run())


def test_plan_20_and_renewal_keeps_that_cap():
    async def _run() -> None:
        accounts, user, tmp = await _store()
        try:
            await apply_event(
                accounts,
                _evt(
                    "evt_sub",
                    "checkout.session.completed",
                    {
                        "mode": "subscription",
                        "customer": "cus_1",
                        "subscription": "sub_1",
                        "metadata": {"user_id": str(user.id), "plan": "20"},
                    },
                ),
            )
            active = await accounts.get_user(user.id)
            assert active is not None
            assert active.llm_cap_usd == 3.0
            assert active.billing_plan == "20"

            await apply_event(
                accounts,
                _evt(
                    "evt_inv",
                    "invoice.paid",
                    {
                        "customer": "cus_1",
                        "subscription": "sub_1",
                        "billing_reason": "subscription_cycle",
                        "period_end": 1893456000,
                    },
                ),
            )
            renewed = await accounts.get_user(user.id)
            assert renewed is not None
            assert renewed.llm_cap_usd == 3.0
            assert renewed.billing_plan == "20"
            assert renewed.billing_status == "active"
        finally:
            tmp.cleanup()

    asyncio.run(_run())


def test_payment_failed_keeps_access_until_deleted():
    async def _run() -> None:
        old = (settings.stripe_secret_key, settings.stripe_price_5)
        settings.stripe_secret_key = "sk_test_x"
        settings.stripe_price_5 = "price_x"
        accounts, user, tmp = await _store()
        try:
            await apply_event(
                accounts,
                _evt(
                    "evt_sub",
                    "checkout.session.completed",
                    {
                        "mode": "subscription",
                        "customer": "cus_1",
                        "subscription": "sub_1",
                        "metadata": {"user_id": str(user.id), "kind": "sub"},
                    },
                ),
            )
            await apply_event(
                accounts,
                _evt(
                    "evt_fail",
                    "invoice.payment_failed",
                    {"customer": "cus_1"},
                ),
            )
            due = await accounts.get_user(user.id)
            assert due is not None
            assert due.billing_status == "past_due"
            assert billing_ok(due) is True

            await apply_event(
                accounts,
                _evt(
                    "evt_del",
                    "customer.subscription.deleted",
                    {
                        "id": "sub_1",
                        "customer": "cus_1",
                        "status": "canceled",
                    },
                ),
            )
            gone = await accounts.get_user(user.id)
            assert gone is not None
            assert gone.billing_status == "canceled"
            assert gone.stripe_subscription_id is None
            assert billing_ok(gone) is False
        finally:
            tmp.cleanup()
            settings.stripe_secret_key, settings.stripe_price_5 = old

    asyncio.run(_run())


def test_unknown_event_ignored():
    async def _run() -> None:
        accounts, _user, tmp = await _store()
        try:
            assert (
                await apply_event(
                    accounts,
                    _evt("evt_ping", "ping", {}),
                )
                == "ignored"
            )
        finally:
            tmp.cleanup()

    asyncio.run(_run())


async def _http_app(tmp: Path):
    settings.console_secret = "test-console-secret-32chars-xxxx"
    settings.storage_db_path = str(tmp / "kore.db")
    settings.vault_root = str(tmp / "vault")
    accounts = AccountStore(str(tmp / "accounts.db"))
    await accounts.init()
    homes = Homes(accounts)
    app = FastAPI()
    app.include_router(console_api_router)
    app.state.accounts = accounts
    app.state.homes = homes
    return app, accounts


def test_checkout_503_without_stripe():
    async def _run() -> None:
        old = (
            settings.console_secret,
            settings.storage_db_path,
            settings.vault_root,
            settings.stripe_secret_key,
            settings.stripe_price_5,
        )
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            settings.stripe_secret_key = ""
            settings.stripe_price_5 = ""
            try:
                app, _accounts = await _http_app(tmp)
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    created = await ac.post(
                        "/api/register",
                        json={"email": "eve@example.com", "password": "password1"},
                    )
                    assert created.status_code == 200
                    chk = await ac.post("/api/billing/checkout", json={"kind": "5"})
                    assert chk.status_code == 503
                    assert chk.json()["detail"] == "stripe_not_configured"
            finally:
                (
                    settings.console_secret,
                    settings.storage_db_path,
                    settings.vault_root,
                    settings.stripe_secret_key,
                    settings.stripe_price_5,
                ) = old

    asyncio.run(_run())


def test_paywall_402_when_stripe_configured():
    async def _run() -> None:
        old = (
            settings.console_secret,
            settings.storage_db_path,
            settings.vault_root,
            settings.stripe_secret_key,
            settings.stripe_price_5,
        )
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            settings.stripe_secret_key = "sk_test_dummy"
            settings.stripe_price_5 = "price_sub"
            try:
                app, _accounts = await _http_app(tmp)
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    created = await ac.post(
                        "/api/register",
                        json={"email": "eve@example.com", "password": "password1"},
                    )
                    assert created.status_code == 200
                    body = created.json()["user"]
                    assert body["billing"]["needed"] is True
                    me = await ac.get("/api/me")
                    assert me.status_code == 200
                    tasks = await ac.get("/api/tasks")
                    assert tasks.status_code == 402
                    assert tasks.json()["detail"] == "billing_required"
            finally:
                (
                    settings.console_secret,
                    settings.storage_db_path,
                    settings.vault_root,
                    settings.stripe_secret_key,
                    settings.stripe_price_5,
                ) = old

    asyncio.run(_run())


def test_signed_webhook_http():
    async def _run() -> None:
        old = (
            settings.console_secret,
            settings.storage_db_path,
            settings.vault_root,
            settings.stripe_secret_key,
            settings.stripe_webhook_secret,
            settings.stripe_price_5,
        )
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            secret = "whsec_test_secret"
            settings.stripe_secret_key = "sk_test_dummy"
            settings.stripe_webhook_secret = secret
            settings.stripe_price_5 = "price_sub"
            try:
                app, accounts = await _http_app(tmp)
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    created = await ac.post(
                        "/api/register",
                        json={"email": "eve@example.com", "password": "password1"},
                    )
                    uid = created.json()["user"]["id"]
                    payload = json.dumps(
                        _evt(
                            "evt_http_1",
                            "checkout.session.completed",
                            {
                                "id": "cs_http",
                                "object": "checkout.session",
                                "mode": "subscription",
                                "customer": "cus_http",
                                "subscription": "sub_http",
                                "client_reference_id": str(uid),
                                "metadata": {
                                    "user_id": str(uid),
                                    "kind": "sub",
                                },
                            },
                        )
                    )
                    sig = WebhookSignature.generate_signature_header(payload, secret)
                    bad = await ac.post(
                        "/api/stripe/webhook",
                        content=payload,
                        headers={
                            "content-type": "application/json",
                            "stripe-signature": "t=1,v1=nope",
                        },
                    )
                    assert bad.status_code == 400
                    ok = await ac.post(
                        "/api/stripe/webhook",
                        content=payload,
                        headers={
                            "content-type": "application/json",
                            "stripe-signature": sig,
                        },
                    )
                    assert ok.status_code == 200, ok.text
                    assert ok.json()["result"] == "ok"
                    user = await accounts.get_user(uid)
                    assert user is not None
                    assert user.billing_status == "active"
                    tasks = await ac.get("/api/tasks")
                    assert tasks.status_code == 200
            finally:
                (
                    settings.console_secret,
                    settings.storage_db_path,
                    settings.vault_root,
                    settings.stripe_secret_key,
                    settings.stripe_webhook_secret,
                    settings.stripe_price_5,
                ) = old

    asyncio.run(_run())


def test_public_pilot_lists_three_plans():
    async def _run() -> None:
        old = (
            settings.console_secret,
            settings.storage_db_path,
            settings.vault_root,
        )
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            try:
                app, _accounts = await _http_app(tmp)
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    r = await ac.get("/api/public/pilot")
                    assert r.status_code == 200
                    plans = r.json()["plans"]
                    assert [p["id"] for p in plans] == ["5", "10", "20"]
                    assert [p["eur"] for p in plans] == [5, 10, 20]
                    assert "credit_usd" not in plans[0]
            finally:
                (
                    settings.console_secret,
                    settings.storage_db_path,
                    settings.vault_root,
                ) = old

    asyncio.run(_run())
