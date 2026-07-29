"""Tests for mission LLM cost accumulation."""

from types import SimpleNamespace

from app.llm.usage_cost import UsageAccumulator, estimate_cost_usd, format_cost_usd


def test_record_completion_with_reported_cost():
    acc = UsageAccumulator()
    resp = SimpleNamespace(
        usage=SimpleNamespace(
            prompt_tokens=1000,
            completion_tokens=500,
            cost=0.0123,
        )
    )
    acc.record_completion(resp, model="deepseek/deepseek-v4-pro")
    assert acc.cost.usd == 0.0123
    assert acc.cost.prompt_tokens == 1000
    assert acc.cost.completion_tokens == 500
    assert acc.cost.llm_calls == 1
    assert acc.cost.estimated is False


def test_record_completion_estimates_when_no_cost():
    acc = UsageAccumulator()
    resp = SimpleNamespace(
        usage=SimpleNamespace(prompt_tokens=1_000_000, completion_tokens=0, cost=None)
    )
    acc.record_completion(resp, model="deepseek/deepseek-v4-pro")
    assert acc.cost.estimated is True
    assert acc.cost.usd == estimate_cost_usd(
        "deepseek/deepseek-v4-pro", prompt_tokens=1_000_000, completion_tokens=0
    )


def test_format_cost_usd():
    assert format_cost_usd(0) == "$0.00"
    assert format_cost_usd(0.0042) == "$0.0042"
    assert format_cost_usd(0.05, estimated=True) == "~$0.050"
