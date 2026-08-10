"""Unit tests for mission report markdown splitting + summary field."""

from __future__ import annotations

from app.kernel.mission_plan import MissionPlan, MissionTask, render_mission_markdown


def _split_mission_markdown(md: str) -> dict:
    """Python port of splitMissionMarkdown for regression tests."""
    text = (md or "").replace("\r\n", "\n").strip()
    if not text:
        return {
            "preamble": "",
            "sections": [],
            "result": None,
            "research": [],
            "detailMarkdown": "",
        }

    lines = text.split("\n")
    preamble: list[str] = []
    sections: list[dict] = []
    current: dict | None = None

    def classify(title: str) -> str:
        t = title.strip().lower()
        if t == "encargo":
            return "encargo"
        if t == "plan":
            return "plan"
        if t == "gasto llm" or t.startswith("gasto"):
            return "gasto"
        return "task"

    def is_meta(kind: str) -> bool:
        return kind in ("encargo", "plan", "gasto")

    def section_md(s: dict) -> str:
        body = s["body"].strip()
        return f"## {s['title']}\n\n{body}" if body else f"## {s['title']}"

    for line in lines:
        if line.startswith("## "):
            if current:
                sections.append(current)
            title = line[3:].strip()
            current = {"title": title, "body": "", "kind": classify(title)}
            continue
        if current is None:
            preamble.append(line)
            continue
        current["body"] += ("\n" if current["body"] else "") + line

    if current:
        sections.append(current)

    for s in sections:
        s["body"] = s["body"].lstrip("\n").rstrip("\n")

    result = next(
        (s for s in sections if s["title"].strip().lower() == "resultado"), None
    )
    research = [s for s in sections if not is_meta(s["kind"]) and s is not result]
    return {
        "preamble": "\n".join(preamble).strip(),
        "sections": sections,
        "result": result,
        "research": research,
        "detailMarkdown": "\n\n".join(section_md(s) for s in research),
    }


SAMPLE = """# Viaje a Lisboa

> Estado: hecho · 3 tareas · $0.12

## Resultado

### Decisión
Ir con B.

### Fuentes
- [B](https://b.example)

## Encargo

Busca opciones de 3 días.

## Plan

- [x] **Recopilar** — opciones

## Recopilar

- Opción A [link](https://a.example)

## Comparar

| Opción | Precio |
| --- | --- |
| A | 100 |
"""


def test_split_resultado_and_single_detail_blob():
    parts = _split_mission_markdown(SAMPLE)
    assert parts["result"] is not None
    assert parts["result"]["title"] == "Resultado"
    assert "Ir con B" in parts["result"]["body"]
    assert [s["title"] for s in parts["research"]] == ["Recopilar", "Comparar"]
    assert "## Recopilar" in parts["detailMarkdown"]
    assert "## Comparar" in parts["detailMarkdown"]


def test_split_without_resultado_has_no_fake_result():
    md = """# X

## Encargo

hola

## Buscar datos

hallazgo 1

## Comparar

elige A
"""
    parts = _split_mission_markdown(md)
    assert parts["result"] is None
    assert [s["title"] for s in parts["research"]] == ["Buscar datos", "Comparar"]


def test_render_puts_summary_first():
    plan = MissionPlan(
        tasks=[
            MissionTask(
                title="Buscar",
                goal="g",
                status="done",
                output="## Buscar\n- a",
            )
        ],
        summary="## Resultado\n\n### Decisión\nHaz X.",
    )
    md = render_mission_markdown("T", "brief", plan, status_line="Estado: hecho")
    assert md.index("## Resultado") < md.index("## Encargo")
    assert md.index("## Resultado") < md.index("## Buscar")


def test_mission_token_budgets():
    from app.kernel.mission_runner import MID_TASK_MAX_TOKENS

    assert MID_TASK_MAX_TOKENS <= 1500


def test_plan_summary_roundtrip():
    plan = MissionPlan(
        tasks=[MissionTask(title="A", goal="g")],
        summary="## Resultado\n\nok",
    )
    again = MissionPlan.from_json(plan.to_json())
    assert again is not None
    assert again.summary.startswith("## Resultado")
