"""FastAPI dependencies that pick fake or real backends (RAG_BACKEND, AUTH_BACKEND)."""

from __future__ import annotations

from app.config import get_settings
from app.contracts import Answerer, User


def get_current_user() -> User:
    """Replaced by app.security.auth.get_current_user in E-006 (owner B)."""
    if get_settings().auth_backend == "fake":
        return User(user_id="dev", department="public")
    from app.security.auth import get_current_user as real

    return real()


def get_answerer() -> Answerer:
    if get_settings().rag_backend == "fake":
        from app.fakes_runtime import CannedAnswerer

        return CannedAnswerer()
    from app.rag.answer import RagAnswerer

    return RagAnswerer()
