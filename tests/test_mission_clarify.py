"""Unit tests for mission brief clarification (no live LLM)."""

from __future__ import annotations

import json

from app.kernel.mission_clarify import (
    MAX_CLARIFY_ROUNDS,
    MAX_QUESTIONS,
    MIN_QUESTIONS_ROUND_1,
    build_clarify_user_payload,
    compose_working_brief,
    parse_clarify_response,
    parse_question,
)


def test_parse_ready_on_round_2():
    r = parse_clarify_response(
        '{"ready": true, "questions": [], "refined_brief": "Buscar barcos 8-12m usados en Mediterráneo"}',
        title="Barcos",
        brief="precios",
        history=[],
        round_n=2,
    )
    assert r.ready
    assert r.questions == []
    assert "barcos" in r.refined_brief.lower()


def test_round_1_never_skips_questions():
    r = parse_clarify_response(
        '{"ready": true, "questions": [], "refined_brief": "Ya está."}',
        title="Barcos",
        brief="quiero un barco",
        history=[],
        round_n=1,
    )
    assert not r.ready
    assert len(r.questions) >= MIN_QUESTIONS_ROUND_1


def test_parse_questions():
    r = parse_clarify_response(
        '{"ready": false, "questions": ["¿Presupuesto?", "¿Nuevo o usado?"], "refined_brief": "Barcos"}',
        title="Barcos",
        brief="quiero un barco",
        history=[],
        round_n=1,
    )
    assert not r.ready
    assert len(r.questions) >= MIN_QUESTIONS_ROUND_1
    assert r.questions[0].prompt == "¿Presupuesto?"
    assert r.questions[1].prompt == "¿Nuevo o usado?"
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
    assert r.questions[0].prompt == "¿Q1?"
    assert r.questions[-1].prompt == f"¿Q{MAX_QUESTIONS}?"


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


def test_fallback_questions_when_empty_json_round_1():
    r = parse_clarify_response(
        "no json here",
        title="Casas",
        brief="Cantabria",
        history=[{"question": "¿Presupuesto?", "answer": "300k"}],
        round_n=1,
    )
    assert not r.ready
    assert len(r.questions) >= MIN_QUESTIONS_ROUND_1
    assert "Casas" in r.refined_brief
    assert "300k" in r.refined_brief


def test_round_2_empty_json_is_ready():
    r = parse_clarify_response(
        "no json here",
        title="Casas",
        brief="Cantabria",
        history=[{"question": "¿Presupuesto?", "answer": "300k"}],
        round_n=2,
    )
    assert r.ready
    assert r.questions == []


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


def test_parse_question_objects_and_strings():
    q = parse_question("¿Presupuesto?")
    assert q is not None
    assert q.prompt == "¿Presupuesto?"
    assert q.choices == []
    obj = parse_question(
        {
            "prompt": "¿Formato?",
            "choices": ["tabla", "veredicto", "tabla", "informe largo"],
            "allow_other": True,
        }
    )
    assert obj is not None
    assert obj.prompt == "¿Formato?"
    assert obj.choices == ["tabla", "veredicto", "informe largo"]


def test_parse_object_questions_in_payload():
    r = parse_clarify_response(
        json.dumps(
            {
                "ready": False,
                "questions": [
                    {
                        "prompt": "¿Presupuesto?",
                        "choices": ["<5k", "5–20k", "sin tope"],
                    },
                    "¿Qué ya descartaste?",
                ],
                "refined_brief": "Barcos",
            }
        ),
        title="Barcos",
        brief="quiero un barco",
        history=[],
        round_n=1,
    )
    assert not r.ready
    assert r.questions[0].choices == ["<5k", "5–20k", "sin tope"]
    assert r.questions[1].prompt == "¿Qué ya descartaste?"
    assert r.questions[1].choices == []


def test_ready_brief_keeps_every_answer():
    history = [
        {"question": "¿Presupuesto?", "answer": "hasta 40k, flexible si hay gang"},
        {
            "question": "¿Zona?",
            "answer": "Cantabria y Asturias, no País Vasco",
        },
        {"question": "¿Formato?", "answer": "tabla comparativa"},
    ]
    r = parse_clarify_response(
        '{"ready": true, "questions": [], "refined_brief": "Buscar piso."}',
        title="Piso",
        brief="un piso cerca del mar",
        history=history,
        round_n=2,
    )
    assert r.ready
    assert "Buscar piso" in r.refined_brief
    assert "hasta 40k" in r.refined_brief
    assert "no País Vasco" in r.refined_brief
    assert "tabla comparativa" in r.refined_brief
    assert "un piso cerca del mar" in r.refined_brief


def test_compose_working_brief_appends_intake():
    text = compose_working_brief(
        "Piso",
        "cerca del mar",
        [{"question": "¿Presupuesto?", "answer": "300k max"}],
        "Corto.",
    )
    assert text.startswith("# Piso")
    assert "Corto." in text
    assert "300k max" in text
    assert "cerca del mar" in text

