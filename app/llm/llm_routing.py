"""Live LLM routing for console (Más drawer)."""

from __future__ import annotations

from app.config import settings

# Approximate OpenRouter list $/1M (in / out). Update when defaults change.
_PRICE: dict[str, tuple[str, str]] = {
    "deepseek/deepseek-v4-pro": ("$0.435", "$0.87"),
    "deepseek/deepseek-v4-flash": ("$0.09", "$0.18"),
    "anthropic/claude-haiku-4.5": ("$1", "$5"),
    "anthropic/claude-sonnet-4.6": ("$3", "$15"),
    "moonshotai/kimi-k2.5": ("$0.375", "$2.03"),
}


def _price(model: str) -> tuple[str, str]:
    return _PRICE.get(model.strip(), ("—", "—"))


def llm_routing() -> dict:
    daily = (settings.openrouter_model or "").strip() or "deepseek/deepseek-v4-pro"
    strong = (settings.openrouter_model_strong or "").strip() or daily
    d_in, d_out = _price(daily)
    s_in, s_out = _price(strong)
    return {
        "rows": [
            {
                "role": "Daily",
                "model": daily,
                "price_in": d_in,
                "price_out": d_out,
                "uses": "Chat normal",
            },
            {
                "role": "Strong",
                "model": strong,
                "price_in": s_in,
                "price_out": s_out,
                "uses": "Dream · Gmail · chat gordo",
            },
            {
                "role": "Misión Normal",
                "model": "deepseek/deepseek-v4-flash",
                "price_in": _price("deepseek/deepseek-v4-flash")[0],
                "price_out": _price("deepseek/deepseek-v4-flash")[1],
                "uses": "Misiones modo Normal",
            },
            {
                "role": "Misión Pro",
                "model": "deepseek/deepseek-v4-pro",
                "price_in": _price("deepseek/deepseek-v4-pro")[0],
                "price_out": _price("deepseek/deepseek-v4-pro")[1],
                "uses": "Misiones Loco / Experto / Duro",
            },
        ],
        "notes": [
            "Precios ~$/1M tokens (lista OpenRouter).",
            "Prompt cache en tool loops (session sticky).",
            "Modo de misión se elige al crear (Nueva): Normal, Loco, Experto, Duro.",
        ],
    }
