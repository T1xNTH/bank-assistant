"""JSON application/server logs with request-scoped correlation, without raw request data."""

from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import PurePath
from traceback import walk_tb
from uuid import uuid4

from app.security.masking import mask_data, mask_identifier, mask_text, masking_active

REQUEST_ID: ContextVar[str] = ContextVar("request_id", default="-")
_HANDLER_NAME = "bank-assistant-json"
_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "TRACE", "CONNECT"}
_STANDARD_FIELDS = frozenset(logging.makeLogRecord({}).__dict__) | {"message", "asctime"}
_SANITIZED = object()


def new_request_id() -> str:
    return str(uuid4())


def http_method(value: object) -> str:
    return value if isinstance(value, str) and value in _METHODS else "OTHER"


def exception_frames(exc: BaseException) -> list[str]:
    """Code locations only: no source lines, absolute paths, locals or exception text."""
    frames = []
    for frame, lineno in walk_tb(exc.__traceback__):
        code = frame.f_code
        frames.append(f"{PurePath(code.co_filename).name}:{lineno}:{code.co_name}")
    return frames[-32:]


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if masking_active():
            return False
        if getattr(record, "_bank_sanitized", None) is _SANITIZED:
            return True
        if not getattr(record, "request_id", None):
            record.request_id = REQUEST_ID.get()
        # Sanitize before any configured handler (including external capture)
        # formats or stores the record. Never render exception text/source lines.
        if record.exc_info and record.exc_info[1] is not None:
            record.exception_type = type(record.exc_info[1]).__name__
            record.exception_frames = exception_frames(record.exc_info[1])
        record.exc_info = None
        record.exc_text = None
        record.stack_info = None
        if record.name == "uvicorn.access":
            message = "http.response"
            if isinstance(record.args, tuple) and len(record.args) == 5:
                record.method = http_method(record.args[1])
                record.status_code = record.args[4]
        else:
            try:
                message = record.getMessage()
            except Exception:
                message = "[REDACTED]"
        record.msg = mask_text(message)
        record.args = ()
        if hasattr(record, "message"):
            record.message = record.msg
        for name, value in list(vars(record).items()):
            # Source metadata and formatter-generated date/time fields are
            # fixed by logging, not application payload. Mask only app extras.
            if name in _STANDARD_FIELDS:
                continue
            if name == "request_id" and isinstance(value, str):
                record.request_id = mask_identifier(value)
            elif isinstance(value, (str, dict, list, tuple)):
                setattr(record, name, mask_data(value))
        record._bank_sanitized = _SANITIZED
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        # Standalone formatters remain safe; configured/multiple handlers share
        # the already sanitized record and never run the analyzer again.
        if not RequestIdFilter().filter(record):
            return json.dumps({"message": "[REDACTED]"})
        fields = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", None) or REQUEST_ID.get(),
            "message": record.getMessage(),
        }
        for name in ("method", "route", "status_code", "duration_ms", "exception_type", "exception_frames"):
            if hasattr(record, name):
                fields[name] = getattr(record, name)
        return json.dumps(fields, ensure_ascii=True)


def configure_logging() -> None:
    """Install one JSON handler; preserve externally installed handlers such as pytest capture."""
    root = logging.getLogger()
    if not any(handler.name == _HANDLER_NAME for handler in root.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler.set_name(_HANDLER_NAME)
        handler.addFilter(RequestIdFilter())
        handler.setFormatter(JsonFormatter())
        root.addHandler(handler)
    root.setLevel(logging.INFO)
    for handler in root.handlers:
        if not any(isinstance(f, RequestIdFilter) for f in handler.filters):
            handler.addFilter(RequestIdFilter())
    # HTTP client INFO messages include complete URLs, potentially containing customer data.
    for name in ("httpx", "httpx2", "httpcore"):
        logging.getLogger(name).setLevel(logging.WARNING)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True
        logger.setLevel(logging.INFO)
    # The middleware emits one richer completion event per request.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
