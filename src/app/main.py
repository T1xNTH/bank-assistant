"""FastAPI entrypoint. Owner: B (routes, auth, errors); /ask logic: A via Answerer."""

from __future__ import annotations

import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import asdict, replace

from fastapi import Depends, FastAPI, HTTPException, Request

from app.agent.api import decide_agent, run_agent
from app.chat import structured_chat
from app.config import get_settings
from app.contracts import LLM, Answerer, User
from app.deps import get_answerer, get_current_user, get_llm
from app.errors import install_error_handlers
from app.log_config import configure_logging, get_logger
from app.middleware import RequestContextMiddleware
from app.queue.jobs import enqueue_job, get_job
from app.rag.answer import AnswerUnavailable, retrieval_mode, warm_up
from app.schemas import AgentResponse, AskRequest, AskResponse, ChatRequest, ChatResponse, ErrorResponse
from app.security.masking import REDACTED, MaskingError, mask_identifier, mask_text, require_mask
from app.tracing import flush, observation

logger = get_logger(__name__)


def _warm_up() -> None:
    try:
        warm_up()
    except Exception as exc:  # the first /ask retries the load and reports its own error
        logger.error("rag.warm_up_failed", extra={"exception_type": type(exc).__name__})
    else:
        logger.info("rag.warm_up_done")


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    if get_settings().rag_backend == "real":
        retrieval_mode()  # a bad RETRIEVAL_MODE stops startup instead of failing every /ask
        # In the background so /health answers while the models load; /ask waits on the same lock.
        threading.Thread(target=_warm_up, name="rag-warm-up", daemon=True).start()
    try:
        yield
    finally:
        flush()
        service = application.state.agent_service
        if service is not None:
            service.checkpointer.conn.close()


def create_app() -> FastAPI:
    configure_logging()
    application = FastAPI(title="bank-assistant", version="0.1.0", lifespan=lifespan)
    application.state.agent_service = None
    application.state.agent_service_lock = threading.Lock()
    install_error_handlers(application)
    application.add_middleware(RequestContextMiddleware)
    application.add_api_route("/health", health, methods=["GET"])
    application.add_api_route(
        "/ask", ask, methods=["POST"], response_model=AskResponse,
        responses={503: {"model": ErrorResponse, "description": "Dependency unavailable"}},
    )
    application.add_api_route("/ask/jobs", enqueue_job, methods=["POST"], status_code=202)
    application.add_api_route("/ask/jobs/{job_id}", get_job, methods=["GET"])
    application.add_api_route(
        "/chat", chat, methods=["POST"], response_model=ChatResponse,
        responses={503: {"model": ErrorResponse, "description": "Dependency unavailable"}},
    )
    application.add_api_route(
        "/agent", run_agent, methods=["POST"], response_model=AgentResponse,
        responses={status: {"model": ErrorResponse} for status in (400, 401, 404, 503)},
    )
    application.add_api_route(
        "/agent/{thread_id}/decision", decide_agent, methods=["POST"], response_model=AgentResponse,
        responses={status: {"model": ErrorResponse} for status in (400, 401, 403, 404, 409, 503)},
    )
    return application


def health() -> dict:
    return {"status": "ok"}


def _mask_input(text: str) -> tuple[str, list[str]]:
    """Masked text and its PII types; 503 when masking is unavailable (fail closed)."""
    try:
        return require_mask(text)
    except MaskingError:
        raise HTTPException(status_code=503, detail="Masking unavailable") from None


def chat(
    req: ChatRequest,
    user: User = Depends(get_current_user),
    llm: LLM = Depends(get_llm),
) -> ChatResponse:
    message = _mask_input(req.message)[0]
    with observation("/chat", root=True, input=message) as trace:
        response = structured_chat(message, llm)
        response = response.model_copy(update={
            "answer": mask_text(response.answer), "model": mask_text(response.model),
        })
        trace.update(output=response.answer, metadata={"intent": response.intent, "needs_human": response.needs_human})
        return response


def ask(
    req: AskRequest,
    request: Request,
    user: User = Depends(get_current_user),
    answerer: Answerer = Depends(get_answerer),
) -> AskResponse:
    request.state.audit_user = user
    # Keep a safe audit value if input masking raises before the next assignment.
    request.state.audit_question = REDACTED
    request.state.audit_question, pii_types = _mask_input(req.question)
    # PII is detected before masking; the answerer only sees masked text (CR-003 C-1, T-026).
    force_local = req.force_local or bool(pii_types)
    try:
        with observation("/ask", root=True, input=request.state.audit_question) as trace:
            result = answerer.answer(request.state.audit_question, user, req.mode, force_local=force_local)
            if trace.trace_id is not None:
                result = replace(result, trace_id=trace.trace_id)
            trace.update(output=result.answer, metadata={"found": result.found, "route": result.route})
    except AnswerUnavailable as exc:
        logger.warning("ask.unavailable: %s", exc, extra={"exception_type": type(exc.__cause__ or exc).__name__})
        raise HTTPException(status_code=503, detail="Answer unavailable") from None
    fields = asdict(result)
    fields["answer"] = mask_text(result.answer)
    fields["citations"] = [dict(c, source=mask_text(c["source"])) for c in fields["citations"]]
    if result.trace_id is not None:
        fields["trace_id"] = mask_identifier(result.trace_id)
    response = AskResponse(**fields)
    request.state.audit_result = result
    return response


app = create_app()
