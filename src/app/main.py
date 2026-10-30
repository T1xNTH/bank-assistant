"""FastAPI entrypoint. Owner: B (routes, auth, errors); /ask logic: A via Answerer."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import Depends, FastAPI

from app.chat import structured_chat
from app.contracts import LLM, Answerer, User
from app.deps import get_answerer, get_current_user, get_llm
from app.errors import install_error_handlers
from app.log_config import configure_logging
from app.middleware import RequestContextMiddleware
from app.schemas import AskRequest, AskResponse, ChatRequest, ChatResponse, ErrorResponse


def create_app() -> FastAPI:
    configure_logging()
    application = FastAPI(title="bank-assistant", version="0.1.0")
    install_error_handlers(application)
    application.add_middleware(RequestContextMiddleware)
    application.add_api_route("/health", health, methods=["GET"])
    application.add_api_route("/ask", ask, methods=["POST"], response_model=AskResponse)
    application.add_api_route(
        "/chat", chat, methods=["POST"], response_model=ChatResponse,
        responses={503: {"model": ErrorResponse, "description": "Dependency unavailable"}},
    )
    return application


def health() -> dict:
    return {"status": "ok"}


def chat(
    req: ChatRequest,
    user: User = Depends(get_current_user),
    llm: LLM = Depends(get_llm),
) -> ChatResponse:
    return structured_chat(req.message, llm)


def ask(
    req: AskRequest,
    user: User = Depends(get_current_user),
    answerer: Answerer = Depends(get_answerer),
) -> AskResponse:
    result = answerer.answer(req.question, user, req.mode)
    return AskResponse(**asdict(result))


app = create_app()
