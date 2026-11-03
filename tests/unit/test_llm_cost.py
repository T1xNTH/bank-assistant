"""Pricing, null semantics and request accounting independent of telemetry."""

from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest

from app.contracts import LLMResult
from app.llm_cost import CURRENT_USAGE, cost_of, usage_scope
from app.tracing import Observation


@pytest.mark.parametrize("model,expected", [
    ("gpt-6-luna", .60), ("openai/gpt-6-luna", .60),
    ("gpt-4.1-mini", 2.0), ("gpt-4.1-mini-2025-04-14", 2.0),
    ("qwen2.5:3b", 0.0), ("ollama_chat/qwen2.5:7b", 0.0),
])
def test_cost_matches_verified_table(model, expected):
    assert cost_of(model, 1_000_000, 1_000_000) == pytest.approx(expected)


def test_fractional_cost_and_known_zero():
    assert cost_of("gpt-6-luna", 125, 50) == pytest.approx(.0000375)
    assert cost_of("gpt-6-luna", 0, 0) == 0.0


@pytest.mark.parametrize("model", ["unknown", "cloud-chat", "fake/cloud-chat", "gpt-6-luna-future"])
def test_unknown_price_is_not_free(model):
    assert cost_of(model, 0, 0) is None
    assert cost_of(model, 100, 50) is None


@pytest.mark.parametrize("count", [-1, 1.5, True, "10", None])
def test_invalid_token_count(count):
    with pytest.raises(ValueError):
        cost_of("gpt-6-luna", count, 1)
    with pytest.raises(ValueError):
        cost_of("gpt-6-luna", 1, count)


def test_aggregate_multiple_calls_unknown_and_missing_usage_without_sdk():
    generation = Observation()
    with usage_scope() as usage:
        assert usage.cost_usd is None
        generation.generation(LLMResult("", "gpt-6-luna", 100, 50))
        generation.generation(LLMResult("", "gpt-4.1-mini", 20, 10))
        assert usage.fields() == {"input_tokens": 120, "output_tokens": 60, "cost_usd": .000059}
        generation.generation(LLMResult("", "unknown", 1, 2))
        assert usage.cost_usd is None and usage.input_tokens == 121
    with usage_scope() as usage:
        generation.generation(LLMResult("", "gpt-6-luna", meta={"usage_known": False}))
        assert usage.cost_usd is None
    assert CURRENT_USAGE.get() is None


def test_concurrent_accounting_and_exception_cleanup():
    def run(i):
        with usage_scope() as usage:
            Observation().generation(LLMResult("", "gpt-6-luna", i, 1))
            return usage.input_tokens

    with ThreadPoolExecutor(max_workers=4) as pool:
        assert list(pool.map(run, range(10))) == list(range(10))
    with pytest.raises(RuntimeError), usage_scope():
        raise RuntimeError("failed")
    assert CURRENT_USAGE.get() is None


def test_export_failure_cannot_discard_accounting():
    def broken(*args):
        raise RuntimeError("export unavailable")

    with usage_scope() as usage:
        Observation(SimpleNamespace(set_attribute=broken)).generation(LLMResult("", "gpt-6-luna", 100, 50))
        assert usage.cost_usd == pytest.approx(.000035)
