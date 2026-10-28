"""Public error envelopes: validation input and internal exception details stay private."""

from __future__ import annotations

from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse

from app.log_config import exception_frames, get_logger, new_request_id

logger = get_logger(__name__)
_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    429: "RATE_LIMITED",
    500: "INTERNAL_ERROR",
    503: "SERVICE_UNAVAILABLE",
}


def error_response(
    request: Request, status: int, code: str, message: str, headers: dict[str, str] | None = None
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None) or new_request_id()
    request.state.request_id = request_id
    response_headers = dict(headers or {})
    response_headers["X-Request-ID"] = request_id
    return JSONResponse({"error": {"code": code, "message": message}}, status_code=status, headers=response_headers)


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    # Pydantic errors include original input; neither the errors nor request body are logged/returned.
    return error_response(request, 400, "BAD_REQUEST", "Invalid request")


async def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    try:
        message = HTTPStatus(exc.status_code).phrase
    except ValueError:
        message = "Request failed"
    return error_response(request, exc.status_code, _CODES.get(exc.status_code, "HTTP_ERROR"), message, exc.headers)


async def internal_error_handler(request: Request, exc: Exception) -> JSONResponse:
    response = error_response(request, 500, "INTERNAL_ERROR", "Internal Server Error")
    logger.error(
        "request.failed",
        extra={
            "request_id": request.state.request_id,
            "exception_type": type(exc).__name__,
            "exception_frames": exception_frames(exc),
        },
    )
    return response


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(HTTPException, http_error_handler)
    app.add_exception_handler(Exception, internal_error_handler)
