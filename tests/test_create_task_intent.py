"""Detect create-task / calendar intents for forced tool recovery."""

from __future__ import annotations

from app.llm.llm_assistant import (
    wants_create_calendar,
    wants_create_task,
    wants_invite_calendar,
)


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


def test_wants_create_calendar_meeting():
    assert wants_create_calendar("crea una reunión mañana a las 10 con Andrea")
    assert wants_create_calendar("reserva mañana 10-11 foco Kore")
    assert wants_create_calendar("bloquea 90 min el miércoles por la mañana")
    assert wants_create_calendar("mete una cita el jueves a las 9")
    assert wants_create_calendar("pon reunión Boehringer el miércoles a las 9")
    assert wants_create_calendar("hueco para pensar el viernes")
    assert not wants_create_calendar("crea una tarea de la reunión")
    assert not wants_create_calendar("qué tengo en el calendario")


def test_wants_invite_calendar():
    assert wants_invite_calendar("invita a Andrea al de Boehringer")
    assert wants_invite_calendar("invítale el email de andrea@x.com")
    assert not wants_invite_calendar(
        "crea reunión mañana 10 e invita a Andrea"
    )  # create path covers attendees
    assert not wants_invite_calendar("crea una tarea")
