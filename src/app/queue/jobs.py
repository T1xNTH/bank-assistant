"""RQ-backed /ask jobs: bounded enqueue, masked persistence, owner-only polling."""

from __future__ import annotations

import hashlib
import os
from dataclasses import asdict
from functools import lru_cache
from uuid import UUID, uuid4

from fastapi import Depends, HTTPException, Request
from redis import Redis
from redis.exceptions import RedisError, WatchError
from rq import Queue
from rq.exceptions import NoSuchJobError
from rq.job import Job
from rq.serializers import JSONSerializer

from app.contracts import User
from app.deps import get_answerer, get_current_user
from app.log_config import configure_logging
from app.schemas import AskRequest, AskResponse, JobAccepted, JobStatusResponse
from app.security.masking import REDACTED, MaskingError, mask_identifier, mask_text, require_mask_text

RESULT_TTL = 3600
QUEUE_NAME = "ask"


def owner_id(user: User) -> str:
    # Preserve exact ownership even when masking would collapse two identifiers.
    # This is pseudonymization, not anonymization: short IDs remain guessable.
    # API keys are never persisted in Redis.
    return hashlib.sha256(user.user_id.encode("utf-8")).hexdigest()


def masked_result(fields: dict) -> AskResponse:
    response = AskResponse.model_validate(fields)
    return response.model_copy(update={
        "answer": mask_text(response.answer),
        "citations": [c.model_copy(update={"source": mask_text(c.source)}) for c in response.citations],
        "trace_id": mask_identifier(response.trace_id) if response.trace_id is not None else None,
    })


def execute_ask(payload: dict, identity: dict) -> dict:
    """Importable RQ callable. Scheduling/rate limiting belongs to T-025."""
    configure_logging()
    try:
        req = AskRequest.model_validate(payload)
        user = User(**identity)
        result = get_answerer().answer(require_mask_text(req.question), user, req.mode)
        return masked_result(asdict(result)).model_dump(mode="json")
    except Exception:
        # RQ persists exception text: never retain upstream messages with PII.
        raise RuntimeError("Job execution failed") from None


class JobQueue:
    def __init__(self, connection: Redis, max_length: int = 100):
        if max_length < 1:
            raise ValueError("QUEUE_MAX_LENGTH must be positive")
        self.connection = connection
        self.max_length = max_length
        self.queue = Queue(QUEUE_NAME, connection=connection, serializer=JSONSerializer)

    def enqueue(self, req: AskRequest, user: User) -> JobAccepted:
        payload = req.model_dump(mode="json")
        payload["question"] = require_mask_text(req.question)
        identity = {"user_id": owner_id(user), "department": user.department, "role": user.role}
        job = Job.create(
            execute_ask, args=(payload, identity), id=str(uuid4()),
            connection=self.connection, serializer=JSONSerializer,
            meta={"owner": owner_id(user)}, description="Masked ask request",
            result_ttl=RESULT_TTL, failure_ttl=RESULT_TTL,
        )
        # WATCH + MULTI makes the capacity check and enqueue one transaction,
        # including across API processes. A full queue never leaves orphan jobs.
        for _ in range(10):
            with self.connection.pipeline() as pipe:
                try:
                    pipe.watch(self.queue.key)
                    length = pipe.llen(self.queue.key)
                    if length >= self.max_length:
                        raise HTTPException(status_code=503, detail="Queue full")
                    pipe.multi()
                    self.queue.enqueue_job(job, pipeline=pipe)
                    pipe.execute()
                    return JobAccepted(job_id=job.id, position=length + 1)
                except WatchError:
                    continue
        raise HTTPException(status_code=503, detail="Queue busy")

    def status(self, job_id: str, user: User) -> JobStatusResponse:
        try:
            if str(UUID(job_id)) != job_id:
                raise ValueError
        except ValueError:
            raise HTTPException(status_code=404, detail="Job not found") from None
        try:
            job = Job.fetch(job_id, connection=self.connection, serializer=JSONSerializer)
            if job.origin != QUEUE_NAME or job.meta.get("owner") != owner_id(user):
                raise HTTPException(status_code=404, detail="Job not found")
            state = job.get_status()
            status = {
                "queued": "queued", "deferred": "queued", "scheduled": "queued",
                "started": "running", "finished": "done",
                "failed": "failed", "stopped": "failed", "canceled": "failed",
            }.get(state, "queued")
            position = self.queue.get_job_position(job_id) if status == "queued" else None
            result = job.return_value() if status == "done" else None
            return JobStatusResponse(
                job_id=job_id, status=status,
                position=position + 1 if position is not None else None,
                result=masked_result(result) if result is not None else None,
                error="Job execution failed" if status == "failed" else None,
            )
        except NoSuchJobError:
            raise HTTPException(status_code=404, detail="Job not found") from None


@lru_cache(maxsize=1)
def get_job_queue() -> JobQueue:
    return JobQueue(
        Redis.from_url(
            os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"),
            socket_connect_timeout=2, socket_timeout=2,
        ),
        max_length=int(os.getenv("QUEUE_MAX_LENGTH", "100")),
    )


def enqueue_job(
    req: AskRequest, request: Request,
    user: User = Depends(get_current_user), queue: JobQueue = Depends(get_job_queue),
) -> JobAccepted:
    request.state.audit_user = user
    request.state.audit_question = REDACTED
    try:
        request.state.audit_question = require_mask_text(req.question)
        return queue.enqueue(req.model_copy(update={"question": request.state.audit_question}), user)
    except (RedisError, MaskingError):
        raise HTTPException(status_code=503, detail="Queue unavailable") from None


def get_job(
    job_id: str, request: Request,
    user: User = Depends(get_current_user), queue: JobQueue = Depends(get_job_queue),
) -> JobStatusResponse:
    request.state.audit_user = user
    try:
        return queue.status(job_id, user)
    except RedisError:
        raise HTTPException(status_code=503, detail="Queue unavailable") from None

