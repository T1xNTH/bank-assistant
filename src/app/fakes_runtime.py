"""Canned backends used when RAG_BACKEND=fake so the API, queue and n8n
can be built before the real RAG exists. Not used in production."""

from __future__ import annotations

from app.contracts import REFUSAL, AskResult, Citation, RetrievalMode, User


class CannedAnswerer:
    def answer(self, question: str, user: User, mode: RetrievalMode | None = None) -> AskResult:
        if "ngoài phạm vi" in question.lower():
            return AskResult(REFUSAL, False, [], mode or "hybrid_rerank", "cloud", 1)
        return AskResult(
            answer="Phí thường niên thẻ chuẩn là 100.000 VND [1].",
            found=True,
            citations=[Citation(n=1, source="bieu-phi-the.pdf", page=3, score=0.91)],
            retrieval_mode=mode or "hybrid_rerank",
            route="cloud",
            latency_ms=1,
        )
