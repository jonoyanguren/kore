"""Mission mode → model, legend, and prompt posture."""

from app.llm.mission_quality import (
    MODEL_NORMAL,
    MODEL_PRO,
    MODE_SPECS,
    PICKER_MODES,
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
    assert normalize_mode("a fondo") == "experto"
    assert normalize_mode("rápido") == "normal"
    assert normalize_mode("loco") == "loco"
    assert normalize_mode("DURO") == "duro"
    assert resolve_mission_model("normal") == MODEL_NORMAL
    assert resolve_mission_model("experto") == MODEL_PRO
    assert resolve_mission_model("loco") == MODEL_PRO
    assert resolve_mission_model("duro") == MODEL_PRO
    assert resolve_mission_model("pro") == MODEL_PRO
    assert MODEL_NORMAL == "deepseek/deepseek-v4-flash"
    assert MODEL_PRO == "deepseek/deepseek-v4-pro"


def test_afondo_costs_more_than_rapido():
    assert approx_mission_usd("experto") > approx_mission_usd("normal") * 3


def test_mode_options_legend():
    opts = mission_mode_options()
    assert [o["id"] for o in opts] == list(PICKER_MODES)
    assert len(opts) == 2
    by_id = {o["id"]: o for o in opts}
    assert by_id["normal"]["label"] == "Rápido"
    assert "decisión" in by_id["normal"]["legend"].lower()
    assert "decisión" in by_id["normal"]["outcome"].lower()
    assert by_id["experto"]["label"] == "A fondo"
    assert "informe" in by_id["experto"]["legend"].lower()
    assert "evidencia" in by_id["experto"]["outcome"].lower()
    for o in opts:
        assert o["when"]
        assert o["outcome"]
        assert o["approx_label"].startswith("~")
        assert o["model"]
        assert format_approx_range(o["approx_usd"]) == o["approx_label"]
    assert "loco" not in by_id
    assert "duro" not in by_id
    assert set(VALID_MODES) >= {"normal", "loco", "experto", "duro"}


def test_quality_options_alias():
    assert mission_quality_options() == mission_mode_options()


def test_mode_prompts_differ():
    rapido = plan_system_for("normal")
    afondo = plan_system_for("experto")
    loco = plan_system_for("loco")
    duro = plan_system_for("duro")
    assert "decisión" in rapido.lower() or "decidir" in rapido.lower()
    assert "primarias" in afondo.lower() or "contraste" in afondo.lower()
    assert "razonable" in loco.lower() or "absurdo" in loco.lower()
    assert "ATACAN" in duro or "atacan" in duro.lower()
    assert "Decisión" in summary_system_for("normal")
    assert "Incertidumbre" in summary_system_for("experto")
    assert "Mapa" in summary_system_for("loco")
    assert "Peor caso" in summary_system_for("duro")
    assert "25 líneas" not in summary_system_for("normal")
    assert "25 líneas" not in summary_system_for("experto")
    assert MODE_SPECS["normal"].max_tasks <= 4
    assert MODE_SPECS["experto"].min_tasks >= 3
    assert MODE_SPECS["loco"].min_tasks >= 4
