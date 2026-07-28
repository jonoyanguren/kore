"""Unit tests for mission brief clarification (no live LLM)."""

from __future__ import annotations

from app.kernel.mission_clarify import (
    MAX_CLARIFY_ROUNDS,
    parse_clarify_response,
)


def test_parse_ready():
    r = parse_clarify_response(
        '{"ready": true, "questions": [], "refined_brief": "Buscar barcos 8-12m usados en Mediterráneo"}',
        title="Barcos",
        brief="precios",
        history=[],
        round_n=1,
    )
    assert r.ready
    assert r.questions == []
    assert "barcos" in r.refined_brief.lower()


def test_parse_questions():
    r = parse_clarify_response(
        '{"ready": false, "questions": ["¿Presupuesto?", "¿Nuevo o usado?"], "refined_brief": "Barcos"}',
        title="Barcos",
        brief="quiero un barco",
        history=[],
        round_n=1,
    )
    assert not r.ready
    assert len(r.questions) == 2
    assert r.rounds_left == MAX_CLARIFY_ROUNDS - 1


def test_force_ready_on_last_round():
    r = parse_clarify_response(
        '{"ready": false, "questions": ["¿Más?"], "refined_brief": "ok"}',
        title="X",
        brief="y",
        history=[{"question": "¿Zona?", "answer": "Norte"}],
        round_n=MAX_CLARIFY_ROUNDS,
    )
    assert r.ready
    assert r.questions == []


def test_fallback_brief_when_empty_json():
    r = parse_clarify_response(
        "no json here",
        title="Casas",
        brief="Cantabria",
        history=[{"question": "¿Presupuesto?", "answer": "300k"}],
        round_n=1,
    )
    assert r.ready  # no questions → ready
    assert "Casas" in r.refined_brief
    assert "300k" in r.refined_brief
