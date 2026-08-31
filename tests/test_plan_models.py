"""Paid plan → cheaper models on Entrar, hybrid on Holgado."""

from __future__ import annotations

from unittest.mock import patch

from app.accounts.context import CompanionProfile, current_profile
from app.llm.llm_assistant import resolve_model
from app.llm.llm_routing import llm_routing
from app.llm.mission_quality import MODEL_NORMAL, MODEL_PRO, resolve_mission_model
from app.llm.plan_models import FLASH, chat_model, mission_model, model_tier


def _profile(*, plan: str | None, legacy: bool = False) -> CompanionProfile:
    return CompanionProfile(
        user_id=1,
        email="a@x.com",
        owner_name="Ana",
        companion_name="Jone",
        companion_tone="",
        legacy_prompts=legacy,
        onboarded=True,
        billing_plan=plan,
    )


def test_local_without_stripe_stays_hybrid():
    assert model_tier(plan="5", legacy=False) == "hybrid"
    assert resolve_mission_model("experto") == MODEL_PRO


def test_plan_5_is_always_flash():
    token = current_profile.set(_profile(plan="5"))
    try:
        with patch("app.llm.plan_models.billing_enforced", return_value=True):
            assert chat_model(strong=False) == FLASH
            assert chat_model(strong=True) == FLASH
            assert resolve_model(strong=True) == FLASH
            assert resolve_mission_model("normal") == FLASH
            assert resolve_mission_model("duro") == FLASH
            data = llm_routing(plan="5", legacy=False)
            assert data["tier"] == "cheap"
            assert len(data["rows"]) == 1
            assert data["rows"][0]["model"] == FLASH
    finally:
        current_profile.reset(token)


def test_plan_10_flash_daily_haiku_strong():
    with patch("app.llm.plan_models.billing_enforced", return_value=True):
        assert chat_model(strong=False, plan="10", legacy=False) == FLASH
        strong = chat_model(strong=True, plan="10", legacy=False)
        assert strong != FLASH
        assert mission_model("normal", plan="10", legacy=False) == MODEL_NORMAL
        assert mission_model("experto", plan="10", legacy=False) == MODEL_PRO
        data = llm_routing(plan="10", legacy=False)
        assert data["tier"] == "lite"


def test_plan_20_and_legacy_are_hybrid():
    with patch("app.llm.plan_models.billing_enforced", return_value=True):
        assert model_tier(plan="20", legacy=False) == "hybrid"
        assert model_tier(plan="5", legacy=True) == "hybrid"
        daily = chat_model(strong=False, plan="20", legacy=False)
        assert daily != FLASH
        assert mission_model("experto", plan="20", legacy=False) == MODEL_PRO
        data = llm_routing(plan="20", legacy=False)
        assert data["tier"] == "hybrid"
        assert len(data["rows"]) == 4
