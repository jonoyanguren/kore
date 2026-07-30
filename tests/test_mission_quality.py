"""Mission quality → Flash / Pro model mapping."""

from app.llm.mission_quality import (
    MODEL_NORMAL,
    MODEL_PRO,
    approx_mission_usd,
    format_approx_range,
    mission_quality_options,
    normalize_quality,
    resolve_mission_model,
)


def test_normalize_and_resolve():
    assert normalize_quality(None) == "normal"
    assert normalize_quality("pro") == "pro"
    assert normalize_quality("HIGH") == "pro"
    assert resolve_mission_model("normal") == MODEL_NORMAL
    assert resolve_mission_model("pro") == MODEL_PRO
    assert MODEL_NORMAL == "deepseek/deepseek-v4-flash"
    assert MODEL_PRO == "deepseek/deepseek-v4-pro"


def test_pro_costs_more_than_normal():
    assert approx_mission_usd("pro") > approx_mission_usd("normal") * 3


def test_quality_options_shape():
    opts = mission_quality_options()
    assert len(opts) == 2
    ids = {o["id"] for o in opts}
    assert ids == {"normal", "pro"}
    for o in opts:
        assert o["approx_label"].startswith("~")
        assert o["model"]
        assert format_approx_range(o["approx_usd"]) == o["approx_label"]
