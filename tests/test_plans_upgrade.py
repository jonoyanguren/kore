"""Plan ladder for mid-month 'Más mes' upgrade."""

from app.billing.plans import next_plan, upgrade_offer


def test_next_plan_ladder():
    assert next_plan(None) == "10"
    assert next_plan("5") == "10"
    assert next_plan("10") == "20"
    assert next_plan("20") is None
    assert upgrade_offer("5") == {"plan": "10", "eur": 10, "name": "Más"}
    assert upgrade_offer("20") is None
