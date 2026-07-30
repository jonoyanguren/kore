"""Clarify a mission brief with 1–2 questions before launch (cheap daily model)."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

import openai

from app.llm.mission_quality import resolve_mission_model
from app.llm.prompt_cache import openrouter_extra_body, with_system_cache_control

logger = logging.getLogger(__name__)

MAX_CLARIFY_ROUNDS = 2
MAX_QUESTIONS = 2

CLARIFY_SYSTEM = """Eres Jone, assistant de Jon. Ayudas a aclarar un ENCARGO de investigación
ANTES de lanzar una misión en background.

Responde SOLO con JSON válido (sin markdown):
{
  "ready": true|false,
  "questions": ["…"],   // 0–2 preguntas cortas en español si ready=false
  "refined_brief": "…"  // brief accionable consolidado (siempre)
}

Reglas:
- ready=true si el brief ya permite investigar (objetivo, restricciones mínimas).
- Si falta algo clave (presupuesto, zona, tipo, plazo…), ready=false y 1–2 preguntas.
- No inventes datos. refined_brief resume título+encargo+respuestas útiles.
- Máximo 2 preguntas. Tono directo, sin relleno."""


@dataclass
class ClarifyResult:
    ready: bool
    questions: list[str]
    refined_brief: str
    round: int
    rounds_left: int


def _extract_json(text: str) -> dict[str, Any] | None:
    raw = (text or "").strip()
    if not raw:
        return None
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", raw)
        if not m:
            return None
        try:
            data = json.loads(m.group(0))
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None


def build_clarify_user_payload(
    *,
    title: str,
    brief: str,
    history: list[dict[str, str]],
    round_n: int,
) -> str:
    parts = [
        f"Título: {title.strip()}",
        f"Encargo:\n{(brief or '').strip() or '(vacío)'}",
        f"Ronda de aclaración: {round_n}/{MAX_CLARIFY_ROUNDS}",
    ]
    if history:
        lines = []
        for i, turn in enumerate(history, 1):
            q = (turn.get("question") or "").strip()
            a = (turn.get("answer") or "").strip()
            lines.append(f"{i}. P: {q}\n   R: {a or '(sin respuesta)'}")
        parts.append("Respuestas previas:\n" + "\n".join(lines))
    if round_n >= MAX_CLARIFY_ROUNDS:
        parts.append(
            "ÚLTIMA RONDA: marca ready=true y consolida el mejor refined_brief "
            "posible con lo que hay (no más questions)."
        )
    return "\n\n".join(parts)


def parse_clarify_response(
    text: str,
    *,
    title: str,
    brief: str,
    history: list[dict[str, str]],
    round_n: int,
) -> ClarifyResult:
    data = _extract_json(text) or {}
    force_ready = round_n >= MAX_CLARIFY_ROUNDS
    ready = bool(data.get("ready")) or force_ready
    questions: list[str] = []
    if not ready:
        raw_qs = data.get("questions") or []
        if isinstance(raw_qs, list):
            for q in raw_qs:
                s = str(q).strip()
                if s:
                    questions.append(s)
                if len(questions) >= MAX_QUESTIONS:
                    break
        if not questions:
            # Model said not ready but gave no Qs — treat as ready.
            ready = True
    refined = str(data.get("refined_brief") or "").strip()
    if not refined:
        refined = _fallback_brief(title, brief, history)
    rounds_left = max(0, MAX_CLARIFY_ROUNDS - round_n)
    if ready:
        questions = []
    return ClarifyResult(
        ready=ready,
        questions=questions,
        refined_brief=refined,
        round=round_n,
        rounds_left=0 if ready else rounds_left,
    )


def _fallback_brief(
    title: str, brief: str, history: list[dict[str, str]]
) -> str:
    lines = [f"Título: {title.strip()}", (brief or "").strip()]
    for turn in history:
        q = (turn.get("question") or "").strip()
        a = (turn.get("answer") or "").strip()
        if q or a:
            lines.append(f"Q: {q}\nA: {a}")
    return "\n\n".join(x for x in lines if x).strip()


async def clarify_mission(
    llm: openai.AsyncOpenAI,
    *,
    title: str,
    brief: str,
    history: list[dict[str, str]] | None = None,
    round_n: int = 1,
    quality: str = "normal",
) -> ClarifyResult:
    hist = history or []
    round_n = max(1, min(int(round_n), MAX_CLARIFY_ROUNDS))
    model = resolve_mission_model(quality)
    user = build_clarify_user_payload(
        title=title, brief=brief, history=hist, round_n=round_n
    )
    messages = with_system_cache_control(
        [
            {"role": "system", "content": CLARIFY_SYSTEM},
            {"role": "user", "content": user},
        ],
        model=model,
    )
    kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": 800,
        "messages": messages,
        "temperature": 0.2,
    }
    extra = openrouter_extra_body(model=model, session_id=f"mission-clarify-{title[:40]}")
    if extra:
        kwargs["extra_body"] = extra
    try:
        response = await llm.chat.completions.create(**kwargs)
        text = (response.choices[0].message.content or "").strip()
    except Exception:
        logger.exception("Mission clarify LLM failed")
        return ClarifyResult(
            ready=True,
            questions=[],
            refined_brief=_fallback_brief(title, brief, hist),
            round=round_n,
            rounds_left=0,
        )
    return parse_clarify_response(
        text, title=title, brief=brief, history=hist, round_n=round_n
    )
