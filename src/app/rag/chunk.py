"""Chunk pages (recursive + table-aware), keeping source/page metadata.

Owner: A — Epic E-003. See docs/00-project/product-plan.md.
"""

from __future__ import annotations


def chunk_pages(pages: list[dict], size: int = 800, overlap: int = 100) -> list[dict]:
    raise NotImplementedError("E-003")
