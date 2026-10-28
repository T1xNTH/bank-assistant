"""Pure ASGI middleware keeps context available through response start and application logs."""

from __future__ import annotations

from time import perf_counter

from starlette.datastructures import MutableHeaders
from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.errors import internal_error_handler
from app.logging import REQUEST_ID, get_logger, http_method, new_request_id

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
        status = 500

        async def send_with_request_id(message: Message) -> None:
            nonlocal response_started, status
            if message["type"] == "http.response.start":
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
                    logger.error("request.failed_after_start", extra={"exception_type": type(exc).__name__})
                    raise
                response = await internal_error_handler(Request(scope), exc)
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
