"""Plan missions into executable tasks + handoffs between steps (D22)."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from typing import Any

import openai

from app.accounts.context import personalize_prompt
from app.llm.mission_quality import (
    mode_label,
    plan_system_for,
    plan_temperature_for,
    resolve_mission_model,
    summary_system_for,
    summary_temperature_for,
    task_range_for,
)
from app.llm.prompt_cache import openrouter_extra_body, with_system_cache_control
from app.llm.spend_ledger import log_completion
from app.llm.usage_cost import MissionCostInfo, UsageAccumulator, format_cost_usd
from app.storage.memory import MemoryStore

logger = logging.getLogger(__name__)

MAX_TASKS = 6
MIN_TASKS = 2
MAX_HANDOFF_CHARS = 1200

PLAN_SYSTEM = """Eres Jone, planner de investigación de Jon.

Descompón un ENCARGO en tareas concretas y ejecutables en secuencia.
Cada tarea = un objetivo claro que se puede cumplir con búsqueda web y lectura de fuentes.

Responde SOLO JSON válido (sin markdown):
{
  "tasks": [
    {"title": "…", "goal": "…"}
  ]
}

Reglas:
- Entre 2 y 6 tareas, orden lógico (explorar → profundizar → comparar).
- NO pidas un informe final en la última tarea: habrá una pasada aparte de Resultado.
- Cada tarea entrega hallazgos concretos (datos, tabla corta, lista, links).
- Títulos cortos (≤8 palabras). goal = qué entregar.
- No tareas vagas ("investigar más"). Sí accionables ("Comparar 5 modelos en rango de precio X").
- Español. No inventes datos del encargo."""


HANDOFF_SYSTEM = """Eres Jone. Tras completar una tarea de misión, escribes un HANDOFF breve
para la SIGUIENTE tarea (no para Jon).

Responde SOLO texto plano en español, 80–180 palabras:
- Qué quedó resuelto / datos clave / links útiles
- Qué debe hacer la siguiente tarea con eso
- Sin markdown, sin JSON, sin secciones numeradas largas"""


SUMMARY_SYSTEM = """Eres Jone. Cierras una misión de investigación para Jon.

Con el encargo y los hallazgos de las tareas, escribes el RESULTADO final.
Responde SOLO markdown en español empezando por:

## Resultado

### Decisión
(1–3 frases claras)

### Por qué
(2–5 bullets)

### Opciones
(tabla corta o bullets: opción — pros/contras — link)

### Siguiente paso
(una acción concreta)

### Fuentes
(3–8 links)

Máx. ~25 líneas. Sin repetir la investigación cruda. Sin inventar datos ni URLs."""


@dataclass
class MissionTask:
    title: str
    goal: str
    status: str = "pending"
    output: str = ""


@dataclass
class MissionPlan:
    tasks: list[MissionTask] = field(default_factory=list)
    handoff: str = ""
    summary: str = ""
    cost: MissionCostInfo | None = None

    def to_json(self) -> str:
        payload: dict[str, Any] = {
            "tasks": [asdict(t) for t in self.tasks],
            "handoff": self.handoff,
        }
        if self.summary.strip():
            payload["summary"] = self.summary.strip()
        if self.cost is not None and (self.cost.usd > 0 or self.cost.llm_calls > 0):
            payload["cost"] = self.cost.to_dict()
        return json.dumps(payload, ensure_ascii=False)

    @classmethod
    def from_json(cls, raw: str | None) -> MissionPlan | None:
        if not raw or not raw.strip():
            return None
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if not isinstance(data, dict):
            return None
        tasks_raw = data.get("tasks")
        if not isinstance(tasks_raw, list) or not tasks_raw:
            return None
        tasks: list[MissionTask] = []
        for item in tasks_raw:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            goal = str(item.get("goal") or "").strip()
            if not title or not goal:
                continue
            tasks.append(
                MissionTask(
                    title=title,
                    goal=goal,
                    status=str(item.get("status") or "pending"),
                    output=str(item.get("output") or ""),
                )
            )
        if not tasks:
            return None
        handoff = str(data.get("handoff") or "").strip()
        summary = str(data.get("summary") or "").strip()
        cost = MissionCostInfo.from_dict(data.get("cost"))
        return cls(tasks=tasks, handoff=handoff, summary=summary, cost=cost)

    def completed_count(self) -> int:
        return sum(1 for t in self.tasks if t.status == "done")


def _completion_text(message: Any) -> str:
    """Prefer content; DeepSeek V4 often parks JSON in reasoning fields."""
    content = (getattr(message, "content", None) or "").strip()
    if content:
        return content
    for attr in ("reasoning", "reasoning_content"):
        raw = getattr(message, attr, None)
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    extra = getattr(message, "model_extra", None) or {}
    if isinstance(extra, dict):
        for key in ("reasoning", "reasoning_content"):
            raw = extra.get(key)
            if isinstance(raw, str) and raw.strip():
                return raw.strip()
    return ""


def _extract_json(text: str) -> dict[str, Any] | None:
    raw = (text or "").strip()
    if not raw:
        return None
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, count=1)
        raw = re.sub(r"\s*```\s*$", "", raw)
    # Prefer the object that contains "tasks"
    for match in re.finditer(r"\{[\s\S]*\}", raw):
        chunk = match.group(0)
        # Trim to first { … last } balanced-ish via tasks key
        try:
            data = json.loads(chunk)
            if isinstance(data, dict) and "tasks" in data:
                return data
        except json.JSONDecodeError:
            pass
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
            # Trailing commas / soft cleanup
            cleaned = re.sub(r",\s*([}\]])", r"\1", m.group(0))
            try:
                data = json.loads(cleaned)
                return data if isinstance(data, dict) else None
            except json.JSONDecodeError:
                return None


def _normalize_plan(data: dict[str, Any]) -> MissionPlan | None:
    tasks_raw = data.get("tasks")
    if not isinstance(tasks_raw, list):
        return None
    tasks: list[MissionTask] = []
    for item in tasks_raw[:MAX_TASKS]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()[:120]
        goal = str(item.get("goal") or item.get("objetivo") or "").strip()[:500]
        if title and goal:
            tasks.append(MissionTask(title=title, goal=goal))
    if len(tasks) < MIN_TASKS:
        return None
    return MissionPlan(tasks=tasks)


def _fallback_plan(title: str, brief: str) -> MissionPlan:
    """Deterministic plan when the model fails JSON — keep the mission moving."""
    snippet = (brief or title or "el encargo").strip()
    if len(snippet) > 220:
        snippet = snippet[:217] + "…"
    return MissionPlan(
        tasks=[
            MissionTask(
                title="Recopilar opciones clave",
                goal=(
                    f"Lista concreta de opciones/sitios relevantes para: {snippet}. "
                    "Incluye por qué valen y links."
                ),
            ),
            MissionTask(
                title="Comparar y completar datos",
                goal=(
                    "Precios/accesos, logística práctica y comparación entre las "
                    "mejores opciones de la tarea anterior."
                ),
            ),
            MissionTask(
                title="Cerrar comparación",
                goal=(
                    "Tabla o bullets con pros/contras y links de las mejores "
                    "opciones; sin informe final largo."
                ),
            ),
        ]
    )


async def _call_planner(
    llm: openai.AsyncOpenAI,
    *,
    model: str,
    messages: list[dict[str, Any]],
    session_id: str,
    usage_acc: UsageAccumulator | None,
    spend_store: MemoryStore | None,
    spend_ref: str | None,
    temperature: float,
) -> str:
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": 1600,
        "temperature": temperature,
    }
    extra = openrouter_extra_body(model=model, session_id=session_id)
    if extra:
        kwargs["extra_body"] = extra
    resp = await llm.chat.completions.create(**kwargs)
    if usage_acc is not None:
        usage_acc.record_completion(resp, model=model)
    await log_completion(
        spend_store,
        resp,
        model=model,
        kind="mission",
        ref=spend_ref,
        session_id=session_id,
    )
    choice = resp.choices[0] if resp.choices else None
    if choice is None or choice.message is None:
        return ""
    return _completion_text(choice.message)


async def plan_mission(
    llm: openai.AsyncOpenAI,
    *,
    title: str,
    brief: str,
    quality: str = "normal",
    usage_acc: UsageAccumulator | None = None,
    spend_store: MemoryStore | None = None,
    spend_ref: str | None = None,
    memory_excerpt: str = "",
) -> MissionPlan:
    model = resolve_mission_model(quality)
    min_t, max_t = task_range_for(quality)
    excerpt = (memory_excerpt or "").strip()
    mem_block = (
        f"Memoria del usuario (digest, no el vault entero):\n{excerpt}\n\n"
        if excerpt
        else ""
    )
    user = (
        f"Título: {title.strip()}\n"
        f"Encargo:\n{(brief or '').strip() or '(vacío)'}\n"
        f"Modo: {mode_label(quality)}\n\n"
        f"{mem_block}"
        f"Genera {min_t}–{max_t} tareas ejecutables.\n"
        'Responde SOLO JSON: {{"tasks":[{{"title":"…","goal":"…"}}]}}'
    )
    base_messages = with_system_cache_control(
        [
            {"role": "system", "content": plan_system_for(quality)},
            {"role": "user", "content": user},
        ],
        model=model,
    )
    session_id = f"mission-plan-{title[:40]}"
    text = await _call_planner(
        llm,
        model=model,
        messages=base_messages,
        session_id=session_id,
        usage_acc=usage_acc,
        spend_store=spend_store,
        spend_ref=spend_ref,
        temperature=plan_temperature_for(quality),
    )
    data = _extract_json(text)
    plan = _normalize_plan(data) if data else None
    if plan is None:
        logger.warning(
            "Mission plan JSON parse failed (len=%d); retrying. preview=%r",
            len(text),
            text[:240],
        )
        retry_messages = list(base_messages) + [
            {"role": "assistant", "content": text or "(vacío)"},
            {
                "role": "user",
                "content": (
                    "Eso no es JSON válido. Responde OTRA VEZ solo con JSON, "
                    'sin markdown ni texto alrededor: {"tasks":[{"title":"…","goal":"…"}]}'
                ),
            },
        ]
        text2 = await _call_planner(
            llm,
            model=model,
            messages=retry_messages,
            session_id=session_id + "-retry",
            usage_acc=usage_acc,
            spend_store=spend_store,
            spend_ref=spend_ref,
            temperature=0.0,
        )
        data2 = _extract_json(text2)
        plan = _normalize_plan(data2) if data2 else None
    if plan is None:
        logger.warning(
            "Mission plan still invalid; using fallback plan for %r",
            title[:40],
        )
        plan = _fallback_plan(title, brief)
    logger.info("Mission plan: %s tasks for %r", len(plan.tasks), title[:40])
    return plan


async def generate_handoff(
    llm: openai.AsyncOpenAI,
    *,
    title: str,
    brief: str,
    completed_task: MissionTask,
    next_task: MissionTask,
    mission_id: int,
    quality: str = "normal",
    usage_acc: UsageAccumulator | None = None,
    spend_store: MemoryStore | None = None,
) -> str:
    model = resolve_mission_model(quality)
    excerpt = (completed_task.output or "").strip()
    if len(excerpt) > 2500:
        excerpt = excerpt[:2490] + "…"
    user = (
        f"Misión: {title.strip()}\n"
        f"Encargo:\n{brief.strip()}\n\n"
        f"Tarea completada: {completed_task.title}\n"
        f"Objetivo cumplido: {completed_task.goal}\n"
        f"Entregable (extracto):\n{excerpt or '(sin texto)'}\n\n"
        f"Siguiente tarea: {next_task.title}\n"
        f"Objetivo siguiente: {next_task.goal}\n\n"
        "Escribe el handoff para la siguiente tarea."
    )
    messages = with_system_cache_control(
        [
            {"role": "system", "content": personalize_prompt(HANDOFF_SYSTEM)},
            {"role": "user", "content": user},
        ],
        model=model,
    )
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": 400,
        "temperature": 0.2,
    }
    session_id = f"mission-{mission_id}-handoff"
    extra = openrouter_extra_body(
        model=model,
        session_id=session_id,
    )
    if extra:
        kwargs["extra_body"] = extra
    resp = await llm.chat.completions.create(**kwargs)
    if usage_acc is not None:
        usage_acc.record_completion(resp, model=model)
    await log_completion(
        spend_store,
        resp,
        model=model,
        kind="mission",
        ref=f"mission:{mission_id}",
        session_id=session_id,
    )
    text = _completion_text(resp.choices[0].message).strip()
    if not text:
        return (
            f"Continuar con: {next_task.title}. "
            f"Contexto previo: {completed_task.title} completada."
        )
    if len(text) > MAX_HANDOFF_CHARS:
        return text[: MAX_HANDOFF_CHARS - 1] + "…"
    return text


def apply_usage_to_plan(plan: MissionPlan, usage_acc: UsageAccumulator) -> None:
    plan.cost = usage_acc.cost


def render_plan_checklist(plan: MissionPlan, *, current_index: int | None) -> str:
    lines = ["## Plan", ""]
    for i, task in enumerate(plan.tasks):
        if task.status == "done":
            mark = "x"
        elif current_index is not None and i == current_index:
            mark = ">"
        else:
            mark = " "
        lines.append(f"- [{mark}] **{task.title}** — {task.goal}")
    lines.append("")
    return "\n".join(lines)


def render_mission_markdown(
    mission_title: str,
    brief: str,
    plan: MissionPlan,
    *,
    status_line: str,
    current_index: int | None = None,
) -> str:
    parts = [
        f"# {mission_title}",
        "",
        f"> {status_line}",
        "",
    ]
    summary = (plan.summary or "").strip()
    if summary:
        if not summary.startswith("##"):
            summary = f"## Resultado\n\n{summary}"
        parts.append(summary.strip())
        parts.append("")
    parts.extend(
        [
            "## Encargo",
            "",
            brief.strip() or "(sin brief)",
            "",
            render_plan_checklist(plan, current_index=current_index),
        ]
    )
    for task in plan.tasks:
        if not task.output.strip():
            continue
        parts.append(task.output.strip())
        parts.append("")
    if plan.cost and plan.cost.usd > 0:
        parts.extend(
            [
                "## Gasto LLM",
                "",
                (
                    f"- **Total:** {format_cost_usd(plan.cost.usd, estimated=plan.cost.estimated)}"
                ),
                f"- Tokens: {plan.cost.prompt_tokens:,} in · "
                f"{plan.cost.completion_tokens:,} out · {plan.cost.llm_calls} llamadas",
            ]
        )
        delta = plan.cost.account_delta_usd
        if delta is not None:
            parts.append(
                f"- Cuenta OpenRouter (delta): {format_cost_usd(delta, estimated=False)}"
            )
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


async def generate_mission_summary(
    llm: openai.AsyncOpenAI,
    *,
    title: str,
    brief: str,
    plan: MissionPlan,
    mission_id: int,
    quality: str = "normal",
    usage_acc: UsageAccumulator | None = None,
    spend_store: MemoryStore | None = None,
    memory_excerpt: str = "",
) -> str:
    """Final pass: one short Resultado from all task outputs."""
    model = resolve_mission_model(quality)
    chunks: list[str] = []
    for i, task in enumerate(plan.tasks, start=1):
        out = (task.output or "").strip()
        if len(out) > 1800:
            out = out[:1790] + "…"
        chunks.append(f"### Tarea {i}: {task.title}\n{out or '(sin texto)'}")
    body = "\n\n".join(chunks) if chunks else "(sin hallazgos)"
    excerpt = (memory_excerpt or "").strip()
    mem_block = (
        f"Memoria del usuario (digest):\n{excerpt}\n\n" if excerpt else ""
    )
    user = (
        f"Misión: {title.strip()}\n"
        f"Modo: {mode_label(quality)}\n"
        f"Encargo:\n{brief.strip()}\n\n"
        f"{mem_block}"
        f"Hallazgos de las tareas:\n\n{body}\n\n"
        "Escribe el Resultado final para el usuario, en el modo indicado."
    )
    messages = with_system_cache_control(
        [
            {"role": "system", "content": summary_system_for(quality)},
            {"role": "user", "content": user},
        ],
        model=model,
    )
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": 2800,
        "temperature": summary_temperature_for(quality),
    }
    session_id = f"mission-{mission_id}-summary"
    extra = openrouter_extra_body(model=model, session_id=session_id)
    if extra:
        kwargs["extra_body"] = extra
    resp = await llm.chat.completions.create(**kwargs)
    if usage_acc is not None:
        usage_acc.record_completion(resp, model=model)
    await log_completion(
        spend_store,
        resp,
        model=model,
        kind="mission",
        ref=f"mission:{mission_id}",
        session_id=session_id,
    )
    text = _completion_text(resp.choices[0].message).strip()
    if not text:
        return "## Resultado\n\n(No pude sintetizar el resultado.)"
    if not text.startswith("##"):
        text = f"## Resultado\n\n{text}"
    elif not text.startswith("## Resultado"):
        rest = text.lstrip("#").strip()
        if rest.lower().startswith("resultado"):
            rest = rest.split("\n", 1)[1] if "\n" in rest else ""
        text = f"## Resultado\n\n{rest.strip()}" if rest.strip() else "## Resultado"
    return text
