"""Fakes for every contract in app.contracts. Use these instead of mocking internals."""

from __future__ import annotations

import re

from app.contracts import REFUSAL, AskResult, Citation, Hit, LLMResult, RetrievalMode, User


class FakeLLM:
    def __init__(self, reply: str = "Câu trả lời [1].") -> None:
        self.reply = reply
        self.calls: list[tuple[list[dict], str]] = []

    def chat(self, messages: list[dict], alias: str, temperature: float = 0.0) -> LLMResult:
        self.calls.append((messages, alias))
        return LLMResult(text=self.reply, model=f"fake/{alias}")


class FakeRetriever:
    def __init__(self, hits: list[Hit] | None = None) -> None:
        self.hits = hits or []

    def retrieve(self, question: str, user: User, k: int) -> list[Hit]:
        allowed = {user.department, "public"}
        return [h for h in self.hits if h.department in allowed][:k]


class FakeAnswerer:
    def __init__(self, retriever: FakeRetriever | None = None) -> None:
        self.retriever = retriever or FakeRetriever()

    def answer(self, question: str, user: User, mode: RetrievalMode | None = None) -> AskResult:
        hits = self.retriever.retrieve(question, user, 5)
        if not hits:
            return AskResult(REFUSAL, False, [], mode or "hybrid_rerank", "cloud", 0)
        cites = [Citation(i + 1, h.source, h.page, h.score) for i, h in enumerate(hits)]
        return AskResult("Trả lời [1].", True, cites, mode or "hybrid_rerank", "cloud", 0)


class FakeMasker:
    _CCCD = re.compile(r"\b\d{12}\b")

    def mask_text(self, text: str) -> tuple[str, list[str]]:
        masked, n = self._CCCD.subn("<CCCD>", text)
        return masked, (["CCCD"] if n else [])
