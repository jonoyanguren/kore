"""Plan missions into executable tasks + handoffs between steps (D22)."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from typing import Any

import openai

from app.llm.llm_assistant import resolve_model
from app.llm.prompt_cache import openrouter_extra_body, with_system_cache_control
from app.llm.usage_cost import MissionCostInfo, UsageAccumulator, format_cost_usd

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
- Entre 2 y 6 tareas, orden lógico (explorar → profundizar → comparar → concluir).
- La ÚLTIMA tarea sintetiza: informe comparativo / recomendación / decisión.
- Títulos cortos (≤8 palabras). goal = qué entregar (datos, tabla, lista, conclusión).
- No tareas vagas ("investigar más"). Sí accionables ("Comparar 5 modelos en rango de precio X").
- Español. No inventes datos del encargo."""


HANDOFF_SYSTEM = """Eres Jone. Tras completar una tarea de misión, escribes un HANDOFF breve
para la SIGUIENTE tarea (no para Jon).

Responde SOLO texto plano en español, 80–180 palabras:
- Qué quedó resuelto / datos clave / links útiles
- Qué debe hacer la siguiente tarea con eso
- Sin markdown, sin JSON, sin secciones numeradas largas"""


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
    cost: MissionCostInfo | None = None

    def to_json(self) -> str:
        payload: dict[str, Any] = {
            "tasks": [asdict(t) for t in self.tasks],
            "handoff": self.handoff,
        }
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
        cost = MissionCostInfo.from_dict(data.get("cost"))
        return cls(tasks=tasks, handoff=handoff, cost=cost)

    def completed_count(self) -> int:
        return sum(1 for t in self.tasks if t.status == "done")


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


def _normalize_plan(data: dict[str, Any]) -> MissionPlan | None:
    tasks_raw = data.get("tasks")
    if not isinstance(tasks_raw, list):
        return None
    tasks: list[MissionTask] = []
    for item in tasks_raw[:MAX_TASKS]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()[:120]
        goal = str(item.get("goal") or "").strip()[:500]
        if title and goal:
            tasks.append(MissionTask(title=title, goal=goal))
    if len(tasks) < MIN_TASKS:
        return None
    return MissionPlan(tasks=tasks)


async def plan_mission(
    llm: openai.AsyncOpenAI,
    *,
    title: str,
    brief: str,
    usage_acc: UsageAccumulator | None = None,
) -> MissionPlan:
    model = resolve_model(strong=False)
    user = (
        f"Título: {title.strip()}\n"
        f"Encargo:\n{(brief or '').strip() or '(vacío)'}\n\n"
        f"Genera {MIN_TASKS}–{MAX_TASKS} tareas ejecutables en JSON."
    )
    extra = openrouter_extra_body(model=model, session_id=f"mission-plan-{title[:40]}")
    resp = await llm.chat.completions.create(
        model=model,
        messages=[
            with_system_cache_control(PLAN_SYSTEM),
            {"role": "user", "content": user},
        ],
        max_tokens=1200,
        temperature=0.3,
        **extra,
    )
    if usage_acc is not None:
        usage_acc.record_completion(resp, model=model)
    text = (resp.choices[0].message.content or "").strip()
    data = _extract_json(text)
    if not data:
        raise RuntimeError("El planner no devolvió JSON válido")
    plan = _normalize_plan(data)
    if plan is None:
        raise RuntimeError("Plan de tareas inválido o demasiado corto")
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
    usage_acc: UsageAccumulator | None = None,
) -> str:
    model = resolve_model(strong=False)
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
    extra = openrouter_extra_body(
        model=model,
        session_id=f"mission-{mission_id}-handoff",
    )
    resp = await llm.chat.completions.create(
        model=model,
        messages=[
            with_system_cache_control(HANDOFF_SYSTEM),
            {"role": "user", "content": user},
        ],
        max_tokens=400,
        temperature=0.2,
        **extra,
    )
    if usage_acc is not None:
        usage_acc.record_completion(resp, model=model)
    text = (resp.choices[0].message.content or "").strip()
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
        "## Encargo",
        "",
        brief.strip() or "(sin brief)",
        "",
        render_plan_checklist(plan, current_index=current_index),
    ]
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
