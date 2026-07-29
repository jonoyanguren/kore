"""Mission plan parsing and rendering."""

from app.kernel.mission_plan import MissionPlan, render_mission_markdown


def test_plan_from_json_roundtrip():
    raw = (
        '{"tasks":[{"title":"A","goal":"g1","status":"done","output":"## A\\nhi"}],'
        '"handoff":"siguiente"}'
    )
    plan = MissionPlan.from_json(raw)
    assert plan is not None
    assert len(plan.tasks) == 1
    assert plan.tasks[0].title == "A"
    assert plan.handoff == "siguiente"
    again = MissionPlan.from_json(plan.to_json())
    assert again is not None
    assert again.tasks[0].goal == "g1"


def test_extract_json_from_fence_and_noise():
    from app.kernel.mission_plan import _extract_json, _fallback_plan, _normalize_plan

    noisy = (
        "Claro, aquí va el plan:\n```json\n"
        '{"tasks":[{"title":"Uno","goal":"g1"},{"title":"Dos","goal":"g2"}]}\n'
        "```\nlisto"
    )
    data = _extract_json(noisy)
    assert data is not None
    plan = _normalize_plan(data)
    assert plan is not None and len(plan.tasks) == 2

    fb = _fallback_plan("Viaje", "Suiza Italia autocaravana")
    assert len(fb.tasks) >= 2


def test_render_mission_markdown_includes_plan_and_output():
    plan = MissionPlan.from_json(
        '{"tasks":[{"title":"Buscar modelos","goal":"5 opciones","status":"done",'
        '"output":"## Buscar modelos\\n| x | [a](https://a.com) |"}]}'
    )
    assert plan is not None
    md = render_mission_markdown(
        "Barcos",
        "encargo",
        plan,
        status_line="Estado: hecho",
    )
    assert "## Plan" in md
    assert "Buscar modelos" in md
    assert "https://a.com" in md
    assert "## Buscar modelos" in md
