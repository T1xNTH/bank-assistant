---
id: audit-development
title: Audit storage and request recording
type: reference
domain: security
module: src/app/security/audit.py
tags: [audit, sqlite, t-015]
priority: 2
---
# Request audit

Every HTTP request produces one committed row in `audit_log` through the request-context middleware, before response headers are released. This includes `/health`, `/chat`, successful and refused `/ask` responses, authentication/validation failures and application errors. WebSocket and lifespan events are excluded. Responses whose headers were already sent are not audited a second time if streaming later fails.

Keeping `/health` audited is intentional: the service is considered ready only when it can commit an audit row, so a database failure produces 503, marks the Compose API container unhealthy, and can make `make up --wait` fail. This preserves the per-HTTP-request audit rule without an unaudited healthcheck exception. The 10-second Compose healthcheck adds about 8,640 rows per day per API container; consumers should filter by endpoint when examining user activity. Retention and indexes remain future work.

The SQLite file defaults to `data/audit.db`; set `AUDIT_DB_PATH` to select a different file in local execution. Parent directories and the table are created on first write. Each call opens its own connection and commits one parameterized INSERT; the application never updates or deletes audit rows. SQLite serializes writers with a 10-second lock timeout. This is application-level append-only storage, not a tamper-proof ledger against administrators with filesystem access.

Compose uses `/app/data/audit.db` on the named `audit_data` volume, surviving API container replacement. `docker compose down --volumes` explicitly deletes that volume; ordinary `down` does not. The API needs write access to the database directory.

Rows follow `docs/05-database/schema.md`: UTC `ts`, authenticated `user_id`/`department`, matched endpoint template, `question_masked`, model `route`, `refused`, request `latency_ms`, `cost_usd` and `trace_id`. Unmatched endpoints use `<unmatched>`; raw URL paths, query strings, request headers and response bodies are never captured. Latency covers application processing until headers, excluding the audit INSERT and client delivery. An available answer trace ID is preserved; otherwise the server-generated `X-Request-ID` correlates the row with logs. Unknown identity, route, refusal or cost remains SQL NULL. `refused=1` means `found=false` in a successful answer, not an HTTP auth/error status. AskResult exposes no cost, so cost stays NULL until future accounting supplies it.

Only validated, authenticated `/ask` requests supply question text to auditing. `audit.mask_question()` calls the existing E-007 `pii.mask_text()` contract. Until that masker is implemented, or if it fails or returns an invalid value, the entire question becomes `[REDACTED]`. `/chat` message bodies are not captured; their question, route, refusal and cost fields remain NULL because ChatResponse does not supply AskResult metadata. Validation/authentication failures retain no question text. This fallback protects the audit boundary; it does not implement E-007 masking of input to models, response output, traces or queues. Do not call `audit.write(question_masked=...)` with raw text.

If SQLite cannot commit, the request returns the existing safe `503 SERVICE_UNAVAILABLE` error envelope rather than an unaudited success. The failed write is logged without exception text or paths and is not retried in the error path. The upstream answer may already have been generated; this is not a distributed transaction with model execution. A failed audit write cannot itself be recorded in the unavailable database.

Run `pytest tests/security/test_audit.py` for audit behavior, privacy, error paths and concurrent requests. The default suite also checks existing auth/API/error envelopes. Tests use temporary database files and synthetic input; they do not modify the deployment audit database.
