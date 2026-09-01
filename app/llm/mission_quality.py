"""Per-mission mode → model, prompts, UI legend, cost estimates.

Picker is two jobs (Rápido / A fondo). Legacy loco/duro/pro still load.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.llm.usage_cost import estimate_cost_usd

MissionMode = Literal["normal", "loco", "experto", "duro"]

MODE_NORMAL: MissionMode = "normal"
MODE_LOCO: MissionMode = "loco"
MODE_EXPERTO: MissionMode = "experto"
MODE_DURO: MissionMode = "duro"
VALID_MODES: tuple[MissionMode, ...] = (
    MODE_NORMAL,
    MODE_LOCO,
    MODE_EXPERTO,
    MODE_DURO,
)
PICKER_MODES: tuple[MissionMode, ...] = (MODE_NORMAL, MODE_EXPERTO)

# Back-compat aliases used in older tests / UI.
QUALITY_NORMAL = MODE_NORMAL
QUALITY_PRO = MODE_EXPERTO
VALID_QUALITIES = VALID_MODES

MODEL_NORMAL = "deepseek/deepseek-v4-flash"
MODEL_PRO = "deepseek/deepseek-v4-pro"

_TYPICAL_PROMPT_TOKENS = 90_000
_TYPICAL_COMPLETION_TOKENS = 25_000

_PLAN_BASE = """Eres Jone, planner de investigación de Jon.

Descompón un ENCARGO en tareas concretas y ejecutables en secuencia.
Cada tarea = un objetivo claro (web, fuentes, y memoria del usuario si aplica).

Responde SOLO JSON válido (sin markdown):
{
  "tasks": [
    {"title": "…", "goal": "…"}
  ]
}

Reglas:
- NO pidas un informe final en la última tarea: habrá una pasada aparte de Resultado.
- Cada tarea entrega hallazgos concretos (datos, tabla corta, lista, links).
- Títulos cortos (≤8 palabras). goal = qué entregar.
- No tareas vagas ("investigar más"). Sí accionables.
- Español. No inventes datos del encargo.
- Si hay MEMORIA adjunta, úsala: no planifiques re-descubrir lo que el usuario ya tiene guardado."""

_IMAGE_RULE = (
    "Si pones una imagen, copia una URL https que ya salga en los hallazgos "
    "(og:image); si no hay, no inventes markdown de imagen."
)


@dataclass(frozen=True)
class MissionModeSpec:
    id: MissionMode
    label: str
    when: str
    legend: str
    outcome: str
    blurb: str
    plan_addon: str
    task_addon: str
    summary_system: str
    clarify_addon: str
    min_tasks: int
    max_tasks: int
    plan_temperature: float
    summary_temperature: float


MODE_SPECS: dict[MissionMode, MissionModeSpec] = {
    MODE_NORMAL: MissionModeSpec(
        id=MODE_NORMAL,
        label="Rápido",
        when="Salir del bloqueo con una recomendación",
        legend="Te dejo una decisión y un siguiente paso.",
        outcome="Salida: decisión · por qué · opciones · siguiente paso · fuentes",
        blurb="Para desatascar. Flash.",
        min_tasks=2,
        max_tasks=4,
        plan_temperature=0.2,
        summary_temperature=0.3,
        plan_addon=(
            "- Entre 2 y 4 tareas, orden lógico (explorar → comparar → decidir).\n"
            "- Cada tarea deja datos que alimenten UNA decisión, no un ensayo."
        ),
        task_addon=(
            "Modo Rápido: hallazgos concretos, organizados, sin relleno. "
            "Tabla corta si comparas. Cumple SOLO el objetivo de esta tarea."
        ),
        summary_system=f"""Eres Jone. Cierras una misión RÁPIDA: el usuario tiene que poder actuar.

Con el encargo y los hallazgos, escribe un Resultado organizado (no un párrafo flojo).
Responde SOLO markdown en español empezando por:

## Resultado

### Decisión
(1–3 frases claras: qué harías y por qué en una línea)

### Por qué
(3–6 bullets con datos, no opiniones sueltas)

### Opciones
(tabla: opción | pros | contras | link. 3–5 filas si hay material)

### Siguiente paso
(una acción concreta, hoy)

### Fuentes
(3–8 links con título, no URLs sueltas)

Organiza. Tablas > prosa. Cifras y nombres. 30–50 líneas si el material da.
Cero relleno, cero “en conclusión”. Sin inventar datos ni URLs.
{_IMAGE_RULE}""",
        clarify_addon=(
            "Modo Rápido: ronda 1 siempre 5–8 preguntas (ready=false). "
            "Decisión, restricciones, alcance, formato, qué evitar."
        ),
    ),
    MODE_EXPERTO: MissionModeSpec(
        id=MODE_EXPERTO,
        label="A fondo",
        when="Cuando importa acertar",
        legend="Informe denso: opciones comparadas, evidencia y fuentes.",
        outcome="Salida: juicio · evidencia · contraste · qué no está claro · siguiente paso · fuentes",
        blurb="Informe para decidir en serio. Pro.",
        min_tasks=3,
        max_tasks=6,
        plan_temperature=0.1,
        summary_temperature=0.2,
        plan_addon=(
            "- Entre 3 y 6 tareas. Profundiza: fuentes primarias, contraste, números.\n"
            "- Cada tarea deja material reutilizable en el informe (tabla, cifras, cita)."
        ),
        task_addon=(
            "Modo A fondo: denso y organizado. Tablas, cifras, nombres, desacuerdos. "
            "Contrasta fuentes. No resumas en tres bullets flojos. "
            "Cumple SOLO el objetivo de esta tarea."
        ),
        summary_system=f"""Eres Jone. Cierras una misión A FONDO: un informe que se puede usar.

El usuario espera organización de verdad, no un resumen corto.
Responde SOLO markdown en español empezando por:

## Resultado

### Juicio
(1–4 frases; preciso)

### Evidencia
(hallazgos no triviales; qué fuente los sostiene; cifras)

### Opciones
(tabla: opción | qué implica | riesgo | fuente)

### Contraste
(posición A vs B vs C, o “lo que dice X vs Y”)

### Incertidumbre
(qué no está claro, sesgos, agujeros)

### Siguiente paso
(una acción concreta, no “seguir investigando”)

### Fuentes
(5–12 links con título y tipo: primario / review / prensa)

Sé denso: 50–90 líneas si el material da. Tablas cuando compares.
Cero pedagogía de Wikipedia. Cero relleno. Sin inventar datos ni URLs.
{_IMAGE_RULE}""",
        clarify_addon=(
            "Modo A fondo: decisión concreta, constraints, fuentes que fía, "
            "qué ya descartó, tolerancia a incertidumbre. "
            "Ronda 1: siempre 5–8 preguntas (ready=false). Brief completo solo si ready."
        ),
    ),
    MODE_LOCO: MissionModeSpec(
        id=MODE_LOCO,
        label="Loco",
        when="Quieres volumen y rareza, no la opción sensata",
        legend="Volumen y rareza; mapa, no una decisión.",
        outcome="Salida: mapa de opciones (también raras) · una locura · fuentes",
        blurb="Pro — divergente; incluye lo absurdo",
        min_tasks=4,
        max_tasks=6,
        plan_temperature=0.85,
        summary_temperature=0.9,
        plan_addon=(
            "- Entre 4 y 6 tareas, cada una un ÁNGULO distinto (incluso raro o absurdo).\n"
            "- PROHIBIDO filtrar por \"es razonable\", \"realista\" o \"lo que haría cualquiera\".\n"
            "- El plan cubre un mapa amplio, no un embudo hacia una sola opción."
        ),
        task_addon=(
            "Modo Loco: busca opciones raras, laterales, mal vistas o absurdas "
            "además de las obvias. No descarte por realismo. Volumen > consenso."
        ),
        summary_system="""Eres Jone en modo LOCO. Cierras un mapa de posibilidades, NO una decisión sensata.

PROHIBIDO: "seamos realistas", recomendar solo lo obvio, una única Decisión.

Responde SOLO markdown en español empezando por:

## Resultado

### Mapa
(8–12 opciones; mezcla obvias, raras y absurdas. Cada una: 1 línea + por qué existe)

### Las más raras
(3–5 de las más extrañas, con un gancho)

### Si hubiera que elegir una locura
(una, no la razonable)

### Fuentes
(3–8 links)

Organiza. Sin inventar datos ni URLs. Si una idea es especulativa, dilo.""",
        clarify_addon=(
            "Modo Loco: no preguntes por presupuesto realista ni por "
            "\"qué es razonable\". Sí pregunta amplitud del mapa, tabúes, "
            "si incluir absurdo, y para qué se usará el mapa. "
            "Ronda 1: 5–8 preguntas que abran, no que cierren."
        ),
    ),
    MODE_DURO: MissionModeSpec(
        id=MODE_DURO,
        label="Duro",
        when="Quieres que te tumben la idea",
        legend="Te tumba la idea; peor caso, cero ánimo.",
        outcome="Salida: veredicto · por qué falla · peor caso · fuentes",
        blurb="Pro — red team; por qué falla",
        min_tasks=3,
        max_tasks=6,
        plan_temperature=0.35,
        summary_temperature=0.4,
        plan_addon=(
            "- Entre 3 y 6 tareas que ATACAN el encargo (riesgos, falsación, peor caso).\n"
            "- Cero tareas de \"encontrar argumentos a favor\" salvo para tumbarlos después.\n"
            "- Incluye qué se está comiendo Jon / supuestos ocultos."
        ),
        task_addon=(
            "Modo Duro: red team. Busca por qué el encargo falla, qué se come Jon, "
            "peor caso. Cero ánimo, cero \"por el otro lado también\". Sé específico."
        ),
        summary_system="""Eres Jone en modo DURO. Red team: tumba el encargo. Cero ánimo.

Responde SOLO markdown en español empezando por:

## Resultado

### Veredicto
(1–3 frases: por qué la idea es frágil o está mal)

### Por qué falla
(2–5 bullets concretos)

### Qué te comes
(supuestos, costes ocultos, riesgos que el brief ignora)

### Peor caso
(escenario creíble, no caricatura)

### Si aún así
(una condición mínima para no suicidarse con esto — o "no lo hagas")

### Fuentes
(3–8 links)

Sin inventar datos ni URLs. No endulces el cierre.""",
        clarify_addon=(
            "Modo Duro: si no hay tesis, pregunta cuál. Pregunta también "
            "qué se juega, qué no quiere oír, y qué le haría cambiar de idea. "
            "Ronda 1: 5–8 preguntas de ataque. No pidas tono agradable."
        ),
    ),
}


def normalize_mode(raw: str | None) -> MissionMode:
    q = (raw or "").strip().lower()
    if q in ("pro", "high", "calidad", "a fondo", "afondo"):
        return MODE_EXPERTO
    if q in ("rapido", "rápido", "fast"):
        return MODE_NORMAL
    if q in VALID_MODES:
        return q  # type: ignore[return-value]
    return MODE_NORMAL


def normalize_quality(raw: str | None) -> MissionMode:
    """Alias: stored column is still named quality."""
    return normalize_mode(raw)


def mode_spec(raw: str | None) -> MissionModeSpec:
    return MODE_SPECS[normalize_mode(raw)]


def mode_label(raw: str | None) -> str:
    return mode_spec(raw).label


def resolve_mission_model(quality: str | None) -> str:
    from app.llm.plan_models import mission_model

    return mission_model(quality)


def approx_mission_usd(quality: str | None) -> float:
    model = resolve_mission_model(quality)
    return estimate_cost_usd(
        model,
        prompt_tokens=_TYPICAL_PROMPT_TOKENS,
        completion_tokens=_TYPICAL_COMPLETION_TOKENS,
    )


def format_approx_range(usd: float) -> str:
    """Human range around a typical mission cost (~0.5×–1.8×)."""
    low = max(0.005, usd * 0.5)
    high = usd * 1.8

    def _fmt(v: float) -> str:
        if v < 0.01:
            return f"${v:.3f}"
        if v < 1:
            return f"${v:.2f}"
        return f"${v:.1f}"

    return f"~{_fmt(low)}–{_fmt(high)}"


def plan_system_for(quality: str | None) -> str:
    from app.accounts.context import personalize_prompt

    spec = mode_spec(quality)
    return personalize_prompt(f"{_PLAN_BASE}\n\nModo {spec.label}:\n{spec.plan_addon}")


def summary_system_for(quality: str | None) -> str:
    from app.accounts.context import personalize_prompt

    return personalize_prompt(mode_spec(quality).summary_system)


def task_addon_for(quality: str | None) -> str:
    from app.accounts.context import personalize_prompt

    return personalize_prompt(mode_spec(quality).task_addon)


def clarify_addon_for(quality: str | None) -> str:
    from app.accounts.context import personalize_prompt

    return personalize_prompt(mode_spec(quality).clarify_addon)


def task_range_for(quality: str | None) -> tuple[int, int]:
    spec = mode_spec(quality)
    return spec.min_tasks, spec.max_tasks


def plan_temperature_for(quality: str | None) -> float:
    return mode_spec(quality).plan_temperature


def summary_temperature_for(quality: str | None) -> float:
    return mode_spec(quality).summary_temperature


def _option_row(mode_id: MissionMode) -> dict:
    spec = MODE_SPECS[mode_id]
    approx = approx_mission_usd(mode_id)
    return {
        "id": spec.id,
        "label": spec.label,
        "when": spec.when,
        "legend": spec.legend,
        "outcome": spec.outcome,
        "blurb": spec.blurb,
        "model": resolve_mission_model(mode_id),
        "approx_usd": approx,
        "approx_label": format_approx_range(approx),
    }


def mission_mode_options() -> list[dict]:
    """Picker options: Rápido / A fondo."""
    return [_option_row(mode_id) for mode_id in PICKER_MODES]


def mission_quality_options() -> list[dict]:
    return mission_mode_options()
