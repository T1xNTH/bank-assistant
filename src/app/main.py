"""FastAPI entrypoint. Owner: B (routes, auth, errors); /ask logic: A via Answerer."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import Depends, FastAPI, Request

from app.contracts import Answerer, User
from app.deps import get_answerer, get_current_user
from app.errors import install_error_handlers
from app.log_config import configure_logging
from app.middleware import RequestContextMiddleware
from app.schemas import AskRequest, AskResponse
from app.security import audit


def create_app() -> FastAPI:
    configure_logging()
    application = FastAPI(title="bank-assistant", version="0.1.0")
    install_error_handlers(application)
    application.add_middleware(RequestContextMiddleware)
    application.add_api_route("/health", health, methods=["GET"])
    application.add_api_route("/ask", ask, methods=["POST"], response_model=AskResponse)
    return application


def health() -> dict:
    return {"status": "ok"}


def ask(
    req: AskRequest,
    request: Request,
    user: User = Depends(get_current_user),
    answerer: Answerer = Depends(get_answerer),
) -> AskResponse:
    request.state.audit_user = user
    request.state.audit_question = audit.mask_question(req.question)
    result = answerer.answer(req.question, user, req.mode)
    response = AskResponse(**asdict(result))
    request.state.audit_result = result
    return response


app = create_app()
