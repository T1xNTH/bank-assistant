"""Dense, hybrid (RRF) and hybrid+rerank retrieval with RBAC and superseded filters.

Owner: A — Epic E-004 / E-010. See docs/00-project/product-plan.md.
"""

from __future__ import annotations

from app.contracts import Hit, User


def retrieve(question: str, user: User, k: int = 5) -> list[Hit]:
    raise NotImplementedError("E-004")
