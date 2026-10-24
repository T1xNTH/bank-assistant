"""bge-m3 dense + sparse embeddings.

Owner: A — Epic E-003. See docs/00-project/product-plan.md.
"""

from __future__ import annotations

DIM = 1024


def embed(texts: list[str]) -> tuple[list[list[float]], list[dict]]:
    raise NotImplementedError("E-003")
