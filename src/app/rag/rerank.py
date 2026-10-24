"""bge-reranker-v2-m3 CrossEncoder reranking.

Owner: A — Epic E-004. See docs/00-project/product-plan.md.
"""

from __future__ import annotations

from app.contracts import Hit


def rerank(question: str, hits: list[Hit], k: int) -> list[Hit]:
    raise NotImplementedError("E-004")
