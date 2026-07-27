from app.kernel.briefing import (
    parse_dream_sections,
    pick_important_tasks,
    pick_must_not_miss,
)
from app.storage.memory import TaskRow


def test_parse_dream_sections_labeled():
    raw = """
# dream / 2026-07-26

Resumen
Día largo con Kore.

Tareas importantes
- Cerrar PR de layouts
- Revisar dream

Reuniones
- 10:00 sync Kimay
- Ninguna

Ayuda
- Empieza por el board
- No te enredes con CSS

Cierre
Vamos.
"""
    s = parse_dream_sections(raw)
    assert "Cerrar PR de layouts" in s["tasks"]
    assert "10:00 sync Kimay" in s["meetings"]
    assert "Empieza por el board" in s["help"]
    assert "Día largo con Kore." in s["summary"]
    assert "Vamos." not in s["help"]


def test_parse_dream_prep_fallback():
    raw = """
Ayer fue intenso.

Prep de hoy
- Prioriza consola
- Deja Gmail para Phase 2
"""
    s = parse_dream_sections(raw)
    assert "Prioriza consola" in s["help"]


def test_pick_important_tasks_order():
    rows = [
        TaskRow(1, "a", "open", None, 0, None, None, None),
        TaskRow(2, "b", "in_progress", None, 0, None, None, None),
        TaskRow(3, "c", "open", None, 2, None, None, None),
    ]
    picked = pick_important_tasks(rows, limit=2)
    assert [t.id for t in picked] == [2, 3]


def test_pick_must_not_miss_dream_and_due():
    rows = [
        TaskRow(1, "Cerrar PR de layouts web", "open", None, 0, None, None, None),
        TaskRow(2, "Starred one", "in_progress", None, 0, None, None, None),
        TaskRow(3, "Banal", "open", None, 0, None, None, None),
        TaskRow(4, "Pagar ITV", "open", "2026-07-27", 0, None, None, None),
    ]
    picked = pick_must_not_miss(
        rows,
        dream_task_titles=["Cerrar PR de layouts"],
        today="2026-07-27",
        limit=5,
    )
    ids = [t.id for t in picked]
    assert 2 not in ids  # starred excluded
    assert 1 in ids and 4 in ids
    assert 3 not in ids
