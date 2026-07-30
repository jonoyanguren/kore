"""Per-mission quality tier → OpenRouter model + UI estimates."""

from __future__ import annotations

from typing import Literal

from app.llm.usage_cost import estimate_cost_usd

MissionQuality = Literal["normal", "pro"]

QUALITY_NORMAL: MissionQuality = "normal"
QUALITY_PRO: MissionQuality = "pro"
VALID_QUALITIES = (QUALITY_NORMAL, QUALITY_PRO)

# Dedicated mission models (not tied to chat daily/strong).
MODEL_NORMAL = "deepseek/deepseek-v4-flash"
MODEL_PRO = "deepseek/deepseek-v4-pro"

# Rough token budget for a 3-task research mission (plan + tools + outputs).
_TYPICAL_PROMPT_TOKENS = 90_000
_TYPICAL_COMPLETION_TOKENS = 25_000


def normalize_quality(raw: str | None) -> MissionQuality:
    q = (raw or "").strip().lower()
    if q in ("pro", "high", "calidad"):
        return QUALITY_PRO
    return QUALITY_NORMAL


def resolve_mission_model(quality: str | None) -> str:
    if normalize_quality(quality) == QUALITY_PRO:
        return MODEL_PRO
    return MODEL_NORMAL


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


def mission_quality_options() -> list[dict]:
    """Options for Nueva dropdown (label, model, approx price)."""
    rows: list[dict] = []
    for q, label, blurb in (
        (
            QUALITY_NORMAL,
            "Normal",
            "Flash — barato y rápido; bueno para la mayoría",
        ),
        (
            QUALITY_PRO,
            "Pro",
            "V4 Pro — más profundo; ~5× tokens",
        ),
    ):
        model = resolve_mission_model(q)
        approx = approx_mission_usd(q)
        rows.append(
            {
                "id": q,
                "label": label,
                "model": model,
                "blurb": blurb,
                "approx_usd": approx,
                "approx_label": format_approx_range(approx),
            }
        )
    return rows
