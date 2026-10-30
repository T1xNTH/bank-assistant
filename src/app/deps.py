"""FastAPI dependencies that pick fake or real backends (RAG_BACKEND, AUTH_BACKEND)."""

from __future__ import annotations

from app.config import get_settings
from app.contracts import LLM, Answerer
from app.security.auth import get_current_user as get_current_user


def get_llm() -> LLM:
    from app import llm

    return llm


def get_answerer() -> Answerer:
    if get_settings().rag_backend == "fake":
        from app.fakes_runtime import CannedAnswerer

        return CannedAnswerer()
    from app.rag.answer import RagAnswerer

    return RagAnswerer()
