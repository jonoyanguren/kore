"""Unit tests for mission report markdown splitting (mirrors web/src/lib/missionReport.ts)."""

from __future__ import annotations


def _split_mission_markdown(md: str) -> dict:
    """Python port of splitMissionMarkdown for regression tests."""
    text = (md or "").replace("\r\n", "\n").strip()
    if not text:
        return {"preamble": "", "sections": [], "result": None, "research": []}

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

    tasks = [s for s in sections if not is_meta(s["kind"])]
    explicit = next(
        (s for s in tasks if s["title"].strip().lower() == "resultado"), None
    )
    result = explicit if explicit is not None else (tasks[-1] if tasks else None)
    research = [s for s in tasks if s is not result]
    return {
        "preamble": "\n".join(preamble).strip(),
        "sections": sections,
        "result": result,
        "research": research,
    }


SAMPLE = """# Viaje a Lisboa

> Estado: hecho · 3 tareas · $0.12

## Encargo

Busca opciones de 3 días.

## Plan

- [x] **Recopilar** — opciones
- [x] **Comparar** — precios
- [x] **Resultado** — decisión

## Recopilar

- Opción A [link](https://a.example)
- Opción B

## Comparar

| Opción | Precio |
| --- | --- |
| A | 100 |
| B | 80 |

## Resultado

### Decisión
Ir con B.

### Fuentes
- [B](https://b.example)
"""


def test_split_puts_resultado_first_and_collapses_research():
    parts = _split_mission_markdown(SAMPLE)
    assert parts["result"] is not None
    assert parts["result"]["title"] == "Resultado"
    assert "Ir con B" in parts["result"]["body"]
    assert [s["title"] for s in parts["research"]] == ["Recopilar", "Comparar"]
    assert all(s["kind"] != "encargo" for s in parts["research"])


def test_split_falls_back_to_last_task_without_resultado_heading():
    md = """# X

## Encargo

hola

## Buscar datos

hallazgo 1

## Síntesis y recomendación

elige A
"""
    parts = _split_mission_markdown(md)
    assert parts["result"]["title"] == "Síntesis y recomendación"
    assert "elige A" in parts["result"]["body"]
    assert [s["title"] for s in parts["research"]] == ["Buscar datos"]


def test_mission_token_budgets():
    from app.kernel.mission_runner import FINAL_TASK_MAX_TOKENS, MID_TASK_MAX_TOKENS

    assert MID_TASK_MAX_TOKENS <= 1500
    assert FINAL_TASK_MAX_TOKENS >= 2500
    assert FINAL_TASK_MAX_TOKENS > MID_TASK_MAX_TOKENS
