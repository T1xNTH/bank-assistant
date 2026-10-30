"""Pure ASGI middleware keeps context available through response start and application logs."""

from __future__ import annotations

from time import perf_counter

from starlette.concurrency import run_in_threadpool
from starlette.datastructures import MutableHeaders
from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.errors import error_response, internal_error_handler
from app.log_config import REQUEST_ID, exception_frames, get_logger, http_method, new_request_id
from app.security import audit

logger = get_logger(__name__)


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Server-generated IDs avoid trusting/logging arbitrary customer input in an incoming header.
        request_id = new_request_id()
        scope.setdefault("state", {})["request_id"] = request_id
        token = REQUEST_ID.set(request_id)
        started = perf_counter()
        response_started = False
        audit_attempted = False
        audit_failed = False
        status = 500

        async def send_with_request_id(message: Message) -> None:
            nonlocal response_started, status, audit_attempted, audit_failed
            if message["type"] == "http.response.start":
                if not audit_attempted:
                    audit_attempted = True
                    state = scope["state"]
                    user = state.get("audit_user")
                    result = state.get("audit_result")
                    try:
                        # Commit before releasing headers; SQLite work must not block the event loop.
                        await run_in_threadpool(
                            audit.write,
                            user_id=user.user_id if user else None,
                            department=user.department if user else None,
                            endpoint=getattr(scope.get("route"), "path", None) or "<unmatched>",
                            question_masked=state.get("audit_question"),
                            route=result.route if result else None,
                            refused=not result.found if result else None,
                            latency_ms=round((perf_counter() - started) * 1000),
                            trace_id=(result.trace_id if result else None) or request_id,
                        )
                    except Exception:
                        audit_failed = True
                        raise
                response_started = True
                status = message["status"]
                message = dict(message)
                message["headers"] = list(message.get("headers", []))
                MutableHeaders(scope=message)["X-Request-ID"] = request_id
            await send(message)

        try:
            try:
                await self.app(scope, receive, send_with_request_id)
            except Exception as exc:
                if response_started:
                    # Streaming failures cannot change an already sent status/body.
                    logger.error(
                        "request.failed_after_start",
                        extra={"exception_type": type(exc).__name__, "exception_frames": exception_frames(exc)},
                    )
                    raise
                if audit_failed:
                    logger.error("audit.write.failed", extra={"exception_type": type(exc).__name__})
                    response = error_response(Request(scope), 503, "SERVICE_UNAVAILABLE", "Service Unavailable")
                else:
                    response = await internal_error_handler(Request(scope), exc)
                try:
                    await response(scope, receive, send_with_request_id)
                except Exception as error:
                    # The first write may be for an application's unhandled-error response.
                    if not audit_failed or response_started:
                        raise
                    logger.error("audit.write.failed", extra={"exception_type": type(error).__name__})
                    response = error_response(Request(scope), 503, "SERVICE_UNAVAILABLE", "Service Unavailable")
                    await response(scope, receive, send_with_request_id)
        finally:
            try:
                logger.info(
                    "http.request.complete",
                    extra={
                        "method": http_method(scope.get("method")),
                        "route": getattr(scope.get("route"), "path", None),
                        "status_code": status,
                        "duration_ms": round((perf_counter() - started) * 1000, 3),
                    },
                )
            finally:
                REQUEST_ID.reset(token)
