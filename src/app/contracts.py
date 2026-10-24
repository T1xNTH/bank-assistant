"""Internal contracts shared by owner A (AI/data) and owner B (platform).

Changing anything here needs a `contract` PR approved by both owners
(see docs/04-api/contract.md). Every contract has a fake in tests/fakes.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol

REFUSAL = "Không tìm thấy thông tin này trong tài liệu nội bộ hiện có."

Department = Literal["public", "credit", "hr"]
RetrievalMode = Literal["dense", "hybrid", "hybrid_rerank"]
Route = Literal["cloud", "local"]


@dataclass(frozen=True)
class User:
    user_id: str
    department: Department
    role: str = "staff"  # "staff" | "approver" | "service"


@dataclass(frozen=True)
class Hit:
    doc_id: str
    source: str
    page: int
    text: str
    score: float
    department: Department
    classification: str = "public"


@dataclass(frozen=True)
class Citation:
    n: int
    source: str
    page: int
    score: float


@dataclass(frozen=True)
class AskResult:
    answer: str
    found: bool
    citations: list[Citation]
    retrieval_mode: RetrievalMode
    route: Route
    latency_ms: int
    trace_id: str | None = None


@dataclass(frozen=True)
class LLMResult:
    text: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    meta: dict = field(default_factory=dict)


class LLM(Protocol):
    def chat(self, messages: list[dict], alias: str, temperature: float = 0.0) -> LLMResult: ...


class Retriever(Protocol):
    def retrieve(self, question: str, user: User, k: int) -> list[Hit]: ...


class Answerer(Protocol):
    def answer(self, question: str, user: User, mode: RetrievalMode | None = None) -> AskResult: ...


class Masker(Protocol):
    def mask_text(self, text: str) -> tuple[str, list[str]]: ...
