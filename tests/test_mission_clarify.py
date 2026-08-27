"""Unit tests for mission brief clarification (no live LLM)."""

from __future__ import annotations

import json

from app.kernel.mission_clarify import (
    MAX_CLARIFY_ROUNDS,
    MAX_QUESTIONS,
    build_clarify_user_payload,
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


def test_parse_keeps_full_intake():
    qs = [f"¿Q{i}?" for i in range(1, 12)]
    r = parse_clarify_response(
        json.dumps({"ready": False, "questions": qs, "refined_brief": "Barcos"}),
        title="Barcos",
        brief="quiero un barco",
        history=[],
        round_n=1,
    )
    assert not r.ready
    assert len(r.questions) == MAX_QUESTIONS
    assert r.questions[0] == "¿Q1?"
    assert r.questions[-1] == f"¿Q{MAX_QUESTIONS}?"


def test_round_two_caps_followups():
    qs = [f"¿Más {i}?" for i in range(6)]
    r = parse_clarify_response(
        json.dumps({"ready": False, "questions": qs, "refined_brief": "ok"}),
        title="X",
        brief="y",
        history=[{"question": "¿Zona?", "answer": "Norte"}],
        round_n=2,
    )
    assert not r.ready
    assert len(r.questions) == 4


def test_force_ready_after_max_rounds():
    r = parse_clarify_response(
        '{"ready": false, "questions": ["¿Más?"], "refined_brief": "ok"}',
        title="X",
        brief="y",
        history=[{"question": "¿Zona?", "answer": "Norte"}],
        round_n=MAX_CLARIFY_ROUNDS + 1,
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


def test_clarify_payload_includes_memory_excerpt():
    p = build_clarify_user_payload(
        title="X",
        brief="y",
        history=[],
        round_n=1,
        memory_excerpt="### work\n- (id 1) Kimay cierra en septiembre",
    )
    assert "Kimay" in p
    assert "MEMORIA" in p
