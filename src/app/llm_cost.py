"""Token cost table and cost_of().

Owner: B — Epic E-013. See docs/00-project/product-plan.md.
"""

from __future__ import annotations


def cost_of(model: str, input_tokens: int, output_tokens: int) -> float:
    raise NotImplementedError("E-013")
