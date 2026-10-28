---
id: api-foundation-development
title: API errors and request logging
type: reference
domain: platform
module: src/app
tags: [api, logging, request-id, t-004]
priority: 2
---
# API errors and request logging

Every HTTP response carries a server-generated UUID4 `X-Request-ID`. Incoming IDs are replaced to prevent customer data or forged correlation values entering logs. Concurrent requests use separate ContextVars; outside a request the ID is `-`.

Use `app.logging.get_logger(__name__)` and static event names. The root handler writes one JSON object per line with timestamp, level, logger, request_id and message. Optional fields are method, static route template, status_code, duration_ms and exception_type. Never put customer data, bodies, queries, credentials or exception messages in log messages. This helper does not mask arbitrary messages; future masking/audit work remains separate. HTTP client INFO logs are disabled, and Uvicorn access logs omit raw URLs and client addresses.

Validation failures return HTTP 400 with `{"error":{"code":"BAD_REQUEST","message":"Invalid request"}}`. HTTP exceptions preserve status and relevant headers, use stable codes and standard status phrases, and omit caller-supplied details. Unhandled errors return HTTP 500 with code `INTERNAL_ERROR` and message `Internal Server Error`; logs contain only the exception type. Once a streaming response has started, its status/body cannot be rewritten; the failure is logged and propagated.

Run `pytest tests/api/test_errors.py tests/api/test_request_logging.py` and `make check` under WSL/Linux. Request context tests cover overlap, header correlation, reset and sensitive input omission. Native Windows Python 3.13 logging crash investigation is tracked in ISSUE-010. The accepted prose contract already requires 400; static OpenAPI alignment is still pending CR-003 approval and is not changed by T-004.
