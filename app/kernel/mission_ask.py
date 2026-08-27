"""Follow-up questions on a finished mission report (does not relaunch)."""

from __future__ import annotations

import json
import logging
from typing import Any

import openai

from app.accounts.context import personalize_prompt
from app.llm.mission_quality import resolve_mission_model
from app.llm.prompt_cache import openrouter_extra_body, with_system_cache_control
from app.llm.spend_ledger import log_completion
from app.storage.memory import MemoryStore

logger = logging.getLogger(__name__)

MAX_REPORT_CHARS = 14_000
MAX_HISTORY = 8

ASK_SYSTEM = """Eres el companion del usuario. Respondes preguntas sobre UNA misión
ya ejecutada. El informe adjunto es la fuente.

Reglas:
- Español, breve, accionable. Markdown corto.
- Si está en el informe, úsalo (citas o bullets). No inventes datos ni URLs.
- Si no está, dilo y sugiere qué habría que relanzar o buscar.
- No relances la misión ni descompongas nuevas tareas.
- No vuelques el informe entero."""


def clip_mission_report(md: str, *, max_chars: int = MAX_REPORT_CHARS) -> str:
    text = (md or "").strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1] + "…"


def parse_ask_events(rows: list[tuple[str, str | None]]) -> list[dict[str, str]]:
    """rows = (kind, payload) oldest→newest."""
    out: list[dict[str, str]] = []
    for kind, payload in rows:
        if kind != "ask" or not payload:
            continue
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        q = str(data.get("q") or "").strip()
        a = str(data.get("a") or "").strip()
        if q and a:
            out.append({"q": q, "a": a})
    return out


def _history_block(history: list[dict[str, str]]) -> str:
    if not history:
        return ""
    lines = []
    for i, turn in enumerate(history[-MAX_HISTORY:], 1):
        q = (turn.get("q") or "").strip()
        a = (turn.get("a") or "").strip()
        if not q:
            continue
        lines.append(f"{i}. P: {q}\n   R: {a or '(sin respuesta)'}")
    if not lines:
        return ""
    return "Preguntas previas:\n" + "\n".join(lines) + "\n\n"


async def ask_mission(
    llm: openai.AsyncOpenAI,
    *,
    title: str,
    markdown: str,
    question: str,
    history: list[dict[str, str]] | None = None,
    quality: str = "normal",
    mission_id: int,
    spend_store: MemoryStore | None = None,
) -> str:
    model = resolve_mission_model(quality)
    report = clip_mission_report(markdown)
    q = question.strip()
    user = (
        f"Misión: {title.strip()}\n\n"
        f"Informe:\n{report or '(sin informe)'}\n\n"
        f"{_history_block(history or [])}"
        f"Pregunta:\n{q}"
    )
    messages = with_system_cache_control(
        [
            {"role": "system", "content": personalize_prompt(ASK_SYSTEM)},
            {"role": "user", "content": user},
        ],
        model=model,
    )
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": 900,
        "temperature": 0.3,
    }
    session_id = f"mission-{mission_id}-ask"
    extra = openrouter_extra_body(model=model, session_id=session_id)
    if extra:
        kwargs["extra_body"] = extra
    resp = await llm.chat.completions.create(**kwargs)
    await log_completion(
        spend_store,
        resp,
        model=model,
        kind="mission",
        ref=f"mission:{mission_id}",
        session_id=session_id,
    )
    choice = resp.choices[0] if resp.choices else None
    text = ""
    if choice is not None and choice.message is not None:
        text = (choice.message.content or "").strip()
    if not text:
        return "No pude responder con este informe. Prueba a reformular."
    return text
