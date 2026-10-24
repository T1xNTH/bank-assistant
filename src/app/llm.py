"""Single place that calls LLMs, through the LiteLLM gateway (aliases cloud-chat, local-chat).

Owner: B — Epic E-005. See docs/00-project/product-plan.md.
"""

from __future__ import annotations

from app.contracts import LLMResult


def chat(messages: list[dict], alias: str, temperature: float = 0.0) -> LLMResult:
    raise NotImplementedError("E-005")
