"""Clarify a mission brief with a thorough intake before launch."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

import openai

from app.llm.mission_quality import clarify_addon_for, resolve_mission_model
from app.llm.prompt_cache import openrouter_extra_body, with_system_cache_control

logger = logging.getLogger(__name__)

MAX_CLARIFY_ROUNDS = 2
MAX_QUESTIONS = 8
MIN_QUESTIONS_ROUND_1 = 5
MAX_CHOICES = 6


CLARIFY_SYSTEM = """Eres el companion del usuario. Aclaras un ENCARGO ANTES de lanzar
una misión de investigación en background.

Responde SOLO con JSON válido (sin markdown):
{
  "ready": true|false,
  "questions": [
    {
      "prompt": "…",
      "choices": ["…"],
      "allow_other": true
    }
  ],
  "refined_brief": "…"
}

refined_brief: siempre. NO es un resumen de una línea.
Es el encargo de trabajo COMPLETO. Incluye cada dato concreto de título,
encargo original y respuestas (nombres, cifras, sitios, no-gos, formato).
Estructura en markdown con secciones: Objetivo · Restricciones · Alcance ·
Formato · Datos. Prohibido comprimir media hora de intake a un párrafo.
Si hay 8 respuestas, las 8 tienen que estar. No inventes.

ready=true SOLO si el brief ya cubre, de forma usable:
- qué decisión o entregable se espera
- restricciones (dinero, sitio, plazo, must / must-not)
- alcance (qué entra y qué no)
- formato / profundidad
- qué ya sabe o no quiere repetir

Si falta más de uno de esos, ready=false.

Preguntas:
- Una idea por pregunta. Cortas, en español, concretas.
- No preguntes lo que ya está en el encargo, en respuestas previas, o en MEMORIA.
- Huecos típicos: para qué / decisión; presupuesto o rango; zona o ámbito;
  plazo; qué ya investigó; fuentes que fía o evita; formato (tabla, comparativa,
  veredicto); criterio de éxito; qué NO hacer.
- Si hay 2–6 respuestas típicas (sí/no, rangos, formatos, prioridad, zona genérica),
  PON "choices" cortas (≤6 palabras, máx. 6). allow_other=true salvo sí/no estricto.
- Pregunta abierta (nombre, historia, URL, “explica”) → "choices": [].
- Ronda 1: 5–8 preguntas. No marques ready=true con un encargo vago.
- Ronda 2: 0–4 preguntas solo de huecos críticos. Si ya se puede trabajar, ready=true.
"""


@dataclass
class ClarifyQuestion:
    prompt: str
    choices: list[str] = field(default_factory=list)
    allow_other: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "prompt": self.prompt,
            "choices": list(self.choices),
            "allow_other": self.allow_other,
        }


@dataclass
class ClarifyResult:
    ready: bool
    questions: list[ClarifyQuestion]
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
    memory_excerpt: str = "",
) -> str:
    parts = [
        f"Título: {title.strip()}",
        f"Encargo:\n{(brief or '').strip() or '(vacío)'}",
        f"Ronda de aclaración: {round_n}/{MAX_CLARIFY_ROUNDS}",
    ]
    excerpt = (memory_excerpt or "").strip()
    if excerpt:
        parts.append(
            "MEMORIA del usuario (digest; no el vault entero). "
            "No preguntes esto de nuevo:\n" + excerpt
        )
    if history:
        lines = []
        for i, turn in enumerate(history, 1):
            q = (turn.get("question") or "").strip()
            a = (turn.get("answer") or "").strip()
            lines.append(f"{i}. P: {q}\n   R: {a or '(sin respuesta)'}")
        parts.append("Respuestas previas:\n" + "\n".join(lines))
    if round_n <= 1:
        parts.append(
            f"PRIMERA RONDA: ready=false salvo brief ya completo. "
            f"Haz {MIN_QUESTIONS_ROUND_1}–{MAX_QUESTIONS} preguntas."
        )
    elif round_n > MAX_CLARIFY_ROUNDS:
        parts.append(
            "ÚLTIMA RONDA: marca ready=true y escribe el refined_brief COMPLETO "
            "(todas las respuestas, sin comprimir). No más questions."
        )
    else:
        parts.append(
            "Si siguen huecos críticos, 1–4 preguntas. Si ya se puede investigar, ready=true."
        )
    return "\n\n".join(parts)


def parse_question(raw: object) -> ClarifyQuestion | None:
    if isinstance(raw, str):
        prompt = raw.strip()
        return ClarifyQuestion(prompt=prompt) if prompt else None
    if not isinstance(raw, dict):
        return None
    prompt = str(
        raw.get("prompt") or raw.get("question") or raw.get("text") or ""
    ).strip()
    if not prompt:
        return None
    choices: list[str] = []
    raw_choices = raw.get("choices") or raw.get("options") or []
    if isinstance(raw_choices, list):
        for item in raw_choices:
            text = str(item).strip()
            if text and text not in choices:
                choices.append(text)
            if len(choices) >= MAX_CHOICES:
                break
    allow = raw.get("allow_other")
    allow_other = True if allow is None else bool(allow)
    return ClarifyQuestion(prompt=prompt, choices=choices, allow_other=allow_other)


def compose_working_brief(
    title: str,
    brief: str,
    history: list[dict[str, str]],
    llm_refined: str = "",
) -> str:
    """Launch brief: LLM synthesis plus every answer, never a one-line squash."""
    blocks: list[str] = []
    heading = title.strip()
    if heading:
        blocks.append(f"# {heading}")
    synth = (llm_refined or "").strip()
    if synth:
        blocks.append(synth)
    original = (brief or "").strip()
    if original and original not in synth:
        blocks.append("## Encargo original\n\n" + original)
    answered = [
        turn
        for turn in history
        if (turn.get("question") or "").strip() or (turn.get("answer") or "").strip()
    ]
    if answered:
        lines = ["## Intake"]
        for turn in answered:
            q = (turn.get("question") or "").strip() or "(pregunta)"
            a = (turn.get("answer") or "").strip() or "—"
            lines.append(f"**{q}**\n{a}")
        blocks.append("\n\n".join(lines))
    return "\n\n".join(blocks).strip()


def parse_clarify_response(
    text: str,
    *,
    title: str,
    brief: str,
    history: list[dict[str, str]],
    round_n: int,
) -> ClarifyResult:
    data = _extract_json(text) or {}
    force_ready = round_n > MAX_CLARIFY_ROUNDS
    ready = bool(data.get("ready")) or force_ready
    cap = 4 if round_n > 1 else MAX_QUESTIONS
    questions: list[ClarifyQuestion] = []
    if not ready:
        raw_qs = data.get("questions") or []
        if isinstance(raw_qs, list):
            for raw in raw_qs:
                parsed = parse_question(raw)
                if parsed is None:
                    continue
                questions.append(parsed)
                if len(questions) >= cap:
                    break
        if not questions:
            # Model said not ready but gave no Qs — treat as ready.
            ready = True
    refined = str(data.get("refined_brief") or "").strip()
    if ready:
        questions = []
        refined = compose_working_brief(title, brief, history, refined)
    elif not refined:
        refined = compose_working_brief(title, brief, history, "")
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


async def clarify_mission(
    llm: openai.AsyncOpenAI,
    *,
    title: str,
    brief: str,
    history: list[dict[str, str]] | None = None,
    round_n: int = 1,
    quality: str = "normal",
    memory_excerpt: str = "",
) -> ClarifyResult:
    hist = history or []
    round_n = max(1, min(int(round_n), MAX_CLARIFY_ROUNDS + 1))
    model = resolve_mission_model(quality)
    user = build_clarify_user_payload(
        title=title,
        brief=brief,
        history=hist,
        round_n=round_n,
        memory_excerpt=memory_excerpt,
    )
    from app.accounts.context import personalize_prompt

    system = f"{personalize_prompt(CLARIFY_SYSTEM)}\n\n{clarify_addon_for(quality)}"
    messages = with_system_cache_control(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        model=model,
    )
    kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": 4000,
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
            refined_brief=compose_working_brief(title, brief, hist, ""),
            round=round_n,
            rounds_left=0,
        )
    return parse_clarify_response(
        text, title=title, brief=brief, history=hist, round_n=round_n
    )
