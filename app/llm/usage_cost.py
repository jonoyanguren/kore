"""Accumulate LLM cost/tokens from OpenRouter completion responses."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# $/1M tokens (in, out) — keep in sync with app/llm/llm_routing.py
_MODEL_PRICE_PER_M: dict[str, tuple[float, float]] = {
    "deepseek/deepseek-v4-pro": (0.435, 0.87),
    "deepseek/deepseek-v4-flash": (0.09, 0.18),
    "anthropic/claude-haiku-4.5": (1.0, 5.0),
    "anthropic/claude-sonnet-4.6": (3.0, 15.0),
    "moonshotai/kimi-k2.5": (0.375, 2.03),
}


@dataclass
class MissionCostInfo:
    usd: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    llm_calls: int = 0
    estimated: bool = False
    account_start_usd: float | None = None
    account_end_usd: float | None = None

    @property
    def account_delta_usd(self) -> float | None:
        if self.account_start_usd is None or self.account_end_usd is None:
            return None
        return max(0.0, self.account_end_usd - self.account_start_usd)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "usd": round(self.usd, 4),
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "llm_calls": self.llm_calls,
            "estimated": self.estimated,
        }
        if self.account_start_usd is not None:
            out["account_start_usd"] = round(self.account_start_usd, 4)
        if self.account_end_usd is not None:
            out["account_end_usd"] = round(self.account_end_usd, 4)
        delta = self.account_delta_usd
        if delta is not None:
            out["account_delta_usd"] = round(delta, 4)
        return out

    @classmethod
    def from_dict(cls, raw: Any) -> MissionCostInfo | None:
        if not isinstance(raw, dict):
            return None
        return cls(
            usd=float(raw.get("usd") or 0),
            prompt_tokens=int(raw.get("prompt_tokens") or 0),
            completion_tokens=int(raw.get("completion_tokens") or 0),
            llm_calls=int(raw.get("llm_calls") or 0),
            estimated=bool(raw.get("estimated")),
            account_start_usd=_opt_float(raw.get("account_start_usd")),
            account_end_usd=_opt_float(raw.get("account_end_usd")),
        )


def _opt_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _usage_dict(response: Any) -> dict[str, Any]:
    usage = getattr(response, "usage", None)
    if usage is None:
        return {}
    if isinstance(usage, dict):
        return usage
    if hasattr(usage, "model_dump"):
        try:
            return usage.model_dump()
        except Exception:
            pass
    out: dict[str, Any] = {}
    for key in ("prompt_tokens", "completion_tokens", "total_tokens", "cost"):
        val = getattr(usage, key, None)
        if val is not None:
            out[key] = val
    return out


def estimate_cost_usd(model: str, *, prompt_tokens: int, completion_tokens: int) -> float:
    model = (model or "").strip()
    pin, pout = _MODEL_PRICE_PER_M.get(model, (1.0, 3.0))
    return (prompt_tokens * pin + completion_tokens * pout) / 1_000_000


@dataclass
class UsageAccumulator:
    """Running totals for one mission (persisted in plan_json between ticks)."""

    cost: MissionCostInfo = field(default_factory=MissionCostInfo)

    def load(self, raw: Any) -> None:
        loaded = MissionCostInfo.from_dict(raw)
        if loaded is not None:
            self.cost = loaded

    def record_completion(self, response: Any, *, model: str) -> None:
        usage = _usage_dict(response)
        prompt = int(usage.get("prompt_tokens") or 0)
        completion = int(usage.get("completion_tokens") or 0)
        self.cost.prompt_tokens += prompt
        self.cost.completion_tokens += completion
        self.cost.llm_calls += 1

        reported = usage.get("cost")
        if reported is not None:
            try:
                self.cost.usd += float(reported)
            except (TypeError, ValueError):
                reported = None
        if reported is None and (prompt or completion):
            self.cost.usd += estimate_cost_usd(
                model, prompt_tokens=prompt, completion_tokens=completion
            )
            self.cost.estimated = True

    def set_account_start(self, usage_usd: float) -> None:
        self.cost.account_start_usd = usage_usd

    def set_account_end(self, usage_usd: float) -> None:
        self.cost.account_end_usd = usage_usd

    def to_dict(self) -> dict[str, Any]:
        return self.cost.to_dict()


def format_cost_usd(usd: float, *, estimated: bool = False) -> str:
    if usd <= 0:
        return "$0.00"
    if usd < 0.01:
        text = f"${usd:.4f}"
    elif usd < 1:
        text = f"${usd:.3f}"
    else:
        text = f"${usd:.2f}"
    return f"~{text}" if estimated else text
