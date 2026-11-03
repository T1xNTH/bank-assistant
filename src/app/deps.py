"""FastAPI dependencies that pick fake or real backends (RAG_BACKEND, AUTH_BACKEND)."""

from __future__ import annotations

import sqlite3

from fastapi import Depends, HTTPException, Request

from app.agent.graph import AgentService
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


def get_agent_service(
    request: Request, llm: LLM = Depends(get_llm), answerer: Answerer = Depends(get_answerer)
) -> AgentService:
    """One service per app/process: its thread locks and amount vault span HTTP requests."""
    # FastAPI resolves llm/answerer each request; only the initial construction uses them.
    try:
        with request.app.state.agent_service_lock:
            if request.app.state.agent_service is None:
                request.app.state.agent_service = AgentService(llm=llm, answerer=answerer)
            return request.app.state.agent_service
    except (sqlite3.Error, OSError):
        raise HTTPException(status_code=503, detail="Agent unavailable") from None
