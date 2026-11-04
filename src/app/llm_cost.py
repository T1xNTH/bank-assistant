"""Token cost table and cost_of().

Owner: B — Epic E-013. See docs/00-project/product-plan.md.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass

# Standard, uncached text USD per million tokens; checked 2026-11-03.
# https://developers.openai.com/api/docs/models/gpt-6-luna
# https://developers.openai.com/api/docs/models/gpt-4.1-mini
# Local Ollama models have no provider token charge (infrastructure excluded):
# infrastructure/litellm/config.yaml. Aliases intentionally have no guessed price.
PRICES = {
    "gpt-6-luna": (0.10, 0.50),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1-mini-2025-04-14": (0.40, 1.60),
    "qwen2.5:3b": (0.0, 0.0),
    "qwen2.5:7b": (0.0, 0.0),
}


def cost_of(model: str, input_tokens: int, output_tokens: int) -> float | None:
    """Estimate standard text cost; unknown models are unknown even at zero tokens."""
    if any(type(n) is not int or n < 0 for n in (input_tokens, output_tokens)):
        raise ValueError("Token counts must be non-negative integers")
    # Only explicit provider prefixes are accepted, never arbitrary suffix matching.
    for prefix in ("openai/", "ollama_chat/", "ollama/"):
        if model.startswith(prefix):
            model = model.removeprefix(prefix)
            break
    price = PRICES.get(model)
    if price is None:
        return None
    return (input_tokens * price[0] + output_tokens * price[1]) / 1_000_000


@dataclass
class Usage:
    """Mutable request-local state shared with FastAPI's copied thread context."""

    input_tokens: int = 0
    output_tokens: int = 0
    calls: int = 0
    unknown: bool = False
    total: float = 0.0

    @property
    def cost_usd(self) -> float | None:
        return None if self.unknown or not self.calls else self.total

    def fields(self) -> dict:
        return {"input_tokens": self.input_tokens, "output_tokens": self.output_tokens, "cost_usd": self.cost_usd}


CURRENT_USAGE: ContextVar[Usage | None] = ContextVar("llm_usage", default=None)


@contextmanager
def usage_scope():
    usage = Usage()
    token = CURRENT_USAGE.set(usage)
    try:
        yield usage
    finally:
        CURRENT_USAGE.reset(token)
