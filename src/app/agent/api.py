"""Authenticated /agent transport; graph owns masking, thread access and approval state."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable

from fastapi import Depends, HTTPException, Request

from app.agent.graph import AgentResult, AgentService, AgentUnavailable, DecisionConflict, ThreadNotFound
from app.contracts import User
from app.deps import get_agent_service, get_current_user
from app.schemas import AgentDecision, AgentRequest, AgentResponse
from app.security.masking import REDACTED, MaskingError, require_mask_content


def _audit_input(request: Request, user: User, text: str) -> None:
    request.state.audit_user = user
    request.state.audit_question = REDACTED
    try:
        request.state.audit_question = require_mask_content(text)
    except MaskingError:
        raise HTTPException(status_code=503, detail="Masking unavailable") from None


def _agent_user(req: AgentRequest, request: Request, user: User = Depends(get_current_user)) -> User:
    _audit_input(request, user, req.message)
    return user


def _decision_user(
    thread_id: str, req: AgentDecision, request: Request, user: User = Depends(get_current_user)
) -> User:
    _audit_input(request, user, json.dumps({"thread_id": thread_id, **req.model_dump()}, ensure_ascii=False))
    if user.role != "approver":
        raise HTTPException(status_code=403, detail="Approver role required")
    return user


def _invoke(call: Callable[[], AgentResult]) -> AgentResponse:
    try:
        result = call()
        # T-030's tool replies are templates over masked data. Re-masking their numeric amounts would
        # turn valid loan calculations into ACCOUNT_NUMBER. All free model text is masked at egress.
        answer = result.answer
        if answer is not None and result.answer_source != "tool":
            answer = require_mask_content(answer)
        pending = result.pending_action
        if pending is not None:
            pending = json.loads(require_mask_content(json.dumps(pending, ensure_ascii=False)))
        return AgentResponse(thread_id=result.thread_id, status=result.status, answer=answer, pending_action=pending)
    except ThreadNotFound:
        raise HTTPException(status_code=404, detail="Unknown thread") from None
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden") from None
    except DecisionConflict:
        raise HTTPException(status_code=409, detail="No pending action") from None
    except (AgentUnavailable, MaskingError, sqlite3.Error, OSError, TypeError):
        # Nested malformed model args can make the checkpoint serializer raise TypeError (T-030 F-08).
        # Do not expose provider messages, model args, storage paths or exception text to clients/logs.
        raise HTTPException(status_code=503, detail="Agent unavailable") from None
    except ValueError:
        # Public API contract uses 400 for invalid input, matching the global validation handler.
        raise HTTPException(status_code=400, detail="Invalid request") from None


def run_agent(
    req: AgentRequest,
    user: User = Depends(_agent_user),
    service: AgentService = Depends(get_agent_service),
) -> AgentResponse:
    # Keep the original text inside the trusted service boundary: graph masks it before persistence or
    # model calls, while retaining PII routing and the in-memory numbered amount vault across turns.
    return _invoke(lambda: service.run(user, req.message, req.thread_id))


def decide_agent(
    thread_id: str,
    req: AgentDecision,
    user: User = Depends(_decision_user),
    service: AgentService = Depends(get_agent_service),
) -> AgentResponse:
    return _invoke(lambda: service.decide(thread_id, user, req.approve, req.comment))
