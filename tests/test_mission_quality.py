"""Mission mode → model, legend, and prompt posture."""

from app.llm.mission_quality import (
    MODEL_NORMAL,
    MODEL_PRO,
    MODE_SPECS,
    VALID_MODES,
    approx_mission_usd,
    format_approx_range,
    mission_mode_options,
    mission_quality_options,
    normalize_mode,
    normalize_quality,
    plan_system_for,
    resolve_mission_model,
    summary_system_for,
)


def test_normalize_and_resolve():
    assert normalize_mode(None) == "normal"
    assert normalize_mode("pro") == "experto"
    assert normalize_quality("HIGH") == "experto"
    assert normalize_mode("loco") == "loco"
    assert normalize_mode("DURO") == "duro"
    assert resolve_mission_model("normal") == MODEL_NORMAL
    assert resolve_mission_model("experto") == MODEL_PRO
    assert resolve_mission_model("loco") == MODEL_PRO
    assert resolve_mission_model("duro") == MODEL_PRO
    assert resolve_mission_model("pro") == MODEL_PRO
    assert MODEL_NORMAL == "deepseek/deepseek-v4-flash"
    assert MODEL_PRO == "deepseek/deepseek-v4-pro"


def test_experto_costs_more_than_normal():
    assert approx_mission_usd("experto") > approx_mission_usd("normal") * 3


def test_mode_options_legend():
    opts = mission_mode_options()
    assert [o["id"] for o in opts] == list(VALID_MODES)
    by_id = {o["id"]: o for o in opts}
    assert by_id["normal"]["legend"].startswith("Investiga")
    assert "mapa" in by_id["loco"]["legend"].lower()
    assert "rigor" in by_id["experto"]["legend"].lower()
    assert "tumba" in by_id["duro"]["legend"].lower()
    for o in opts:
        assert o["when"]
        assert o["approx_label"].startswith("~")
        assert o["model"]
        assert format_approx_range(o["approx_usd"]) == o["approx_label"]


def test_quality_options_alias():
    assert mission_quality_options() == mission_mode_options()


def test_mode_prompts_differ():
    loco = plan_system_for("loco")
    experto = plan_system_for("experto")
    duro = plan_system_for("duro")
    assert "razonable" in loco.lower() or "absurdo" in loco.lower()
    assert "básico" in experto.lower()
    assert "ATACAN" in duro or "atacan" in duro.lower()
    assert "Mapa" in summary_system_for("loco")
    assert "Incertidumbre" in summary_system_for("experto")
    assert "Peor caso" in summary_system_for("duro")
    assert "Decisión" in summary_system_for("normal")
    assert MODE_SPECS["loco"].min_tasks >= 4
