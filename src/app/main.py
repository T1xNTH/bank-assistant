"""FastAPI entrypoint. Owner: B (routes, auth, errors); /ask logic: A via Answerer."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import Depends, FastAPI, Request

from app.chat import structured_chat
from app.contracts import LLM, Answerer, User
from app.deps import get_answerer, get_current_user, get_llm
from app.errors import install_error_handlers
from app.log_config import configure_logging
from app.middleware import RequestContextMiddleware
from app.schemas import AskRequest, AskResponse, ChatRequest, ChatResponse, ErrorResponse
from app.security import audit
from app.security.masking import mask_identifier, mask_text


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
    response = structured_chat(mask_text(req.message), llm)
    return response.model_copy(update={"answer": mask_text(response.answer), "model": mask_text(response.model)})


def ask(
    req: AskRequest,
    request: Request,
    user: User = Depends(get_current_user),
    answerer: Answerer = Depends(get_answerer),
) -> AskResponse:
    request.state.audit_user = user
    request.state.audit_question = audit.mask_question(req.question)
    result = answerer.answer(request.state.audit_question, user, req.mode)
    fields = asdict(result)
    fields["answer"] = mask_text(result.answer)
    fields["citations"] = [dict(c, source=mask_text(c["source"])) for c in fields["citations"]]
    if result.trace_id is not None:
        fields["trace_id"] = mask_identifier(result.trace_id)
    response = AskResponse(**fields)
    request.state.audit_result = result
    return response


app = create_app()
