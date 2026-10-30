"""HTTP request/response models. Must match docs/04-api/openapi.yaml. Owner: B."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.contracts import RetrievalMode, Route


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    answer: str
    intent: Literal["question", "complaint", "request", "other"]
    needs_human: bool
    model: str
    latency_ms: int


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    mode: RetrievalMode | None = None
    force_local: bool = False


class CitationOut(BaseModel):
    n: int
    source: str
    page: int
    score: float


class AskResponse(BaseModel):
    answer: str
    found: bool
    citations: list[CitationOut]
    retrieval_mode: RetrievalMode
    route: Route
    latency_ms: int
    trace_id: str | None = None
