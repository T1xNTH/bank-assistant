"""JSON application/server logs with request-scoped correlation, without raw request data."""

from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from uuid import uuid4

REQUEST_ID: ContextVar[str] = ContextVar("request_id", default="-")
_HANDLER_NAME = "bank-assistant-json"
_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "TRACE", "CONNECT"}


def new_request_id() -> str:
    return str(uuid4())


def http_method(value: object) -> str:
    return value if isinstance(value, str) and value in _METHODS else "OTHER"


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not getattr(record, "request_id", None):
            record.request_id = REQUEST_ID.get()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        fields = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", None) or REQUEST_ID.get(),
            "message": record.getMessage() if record.name != "uvicorn.access" else "http.response",
        }
        for name in ("method", "route", "status_code", "duration_ms", "exception_type"):
            if hasattr(record, name):
                fields[name] = getattr(record, name)
        if record.name == "uvicorn.access" and isinstance(record.args, tuple) and len(record.args) == 5:
            # Uvicorn's formatted access message includes the raw URL/query and client address.
            fields["method"] = http_method(record.args[1])
            fields["status_code"] = record.args[4]
        if record.exc_info and record.exc_info[1] is not None:
            # Exception messages/tracebacks can contain customer data or provider credentials.
            fields["exception_type"] = type(record.exc_info[1]).__name__
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
    # HTTP client INFO messages include complete URLs, potentially containing customer data.
    for name in ("httpx", "httpx2", "httpcore"):
        logging.getLogger(name).setLevel(logging.WARNING)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True
        logger.setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
