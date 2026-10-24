"""Qdrant client, collection with dense + sparse vectors and payload indexes.

Owner: A — Epic E-003. See docs/00-project/product-plan.md.
"""

from __future__ import annotations

COLLECTION = "bank_docs"


def ensure_collection() -> None:
    raise NotImplementedError("E-003")


def upsert_chunks(chunks: list[dict]) -> int:
    raise NotImplementedError("E-003")
