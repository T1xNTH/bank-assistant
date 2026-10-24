"""Answerer implementation: retrieve -> prompt -> llm.chat -> citations / refusal.

Owner: A — Epic E-004. See docs/00-project/product-plan.md.
"""

from __future__ import annotations

from app.contracts import AskResult, RetrievalMode, User


class RagAnswerer:
    def answer(self, question: str, user: User, mode: RetrievalMode | None = None) -> AskResult:
        raise NotImplementedError("E-004")
