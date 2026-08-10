"""Detect create-task intent for forced add_task recovery."""

from __future__ import annotations

from app.llm.llm_assistant import wants_create_task


def test_wants_create_task_spanish():
    assert wants_create_task("crea una tarea de llamar a Andrea")
    assert wants_create_task("Añade tarea: enviar factura")
    assert wants_create_task("apunta comprar leche")
    assert wants_create_task("anota revisar el contrato")
    assert wants_create_task("nueva tarea prep call")
    assert wants_create_task("hazme una tarea de follow-up")
    assert not wants_create_task("qué tareas tengo abiertas")
    assert not wants_create_task("cómo va el dream")
    assert not wants_create_task("reserva mañana 10-11 en calendar")
