---
id: adr-0004-rq-queue
title: ADR 0004 — Redis and RQ asynchronous requests
type: reference
domain: architecture
module: queue
tags: [adr, rq, redis, retry, t-043]
priority: 2
---
# ADR 0004 — Redis and RQ asynchronous requests

- **Date**: `2026-11-06`
- **Owner**: `trong-hung`
- **Status**: `Retrospective implemented-design record; T-043 review pending`
- **Authority**: Existing async-job, masking, priority and bounded-retry requirements.

## Context

Retrieval and provider calls can be slow or rate-limited. An HTTP request cannot
wait indefinitely, and accepted work must be bounded, owner-scoped and safe to
persist. The MVP already uses Redis for admission/execution token buckets.

## Decision

Use RQ with JSON serialization on Redis. Authenticated clients submit to
`POST /ask/jobs`, receive HTTP 202 with a job ID and poll `GET /ask/jobs/{job_id}`.
Persist masked request/result data, sanitized failures and a SHA-256 pseudonym
for exact owner checking. Unknown, foreign or expired jobs return 404.

Approvers enqueue to `ask-high`; other roles use `ask-default`, followed by legacy
`ask`. Bound total waiting capacity across queues and reclaim expired waiting jobs.
Default waiting and result TTLs are one hour. Queue positions are snapshots.

The worker uses a shared execution-attempt token bucket, finite typed-429 retry
budget, exponential backoff and job timeout. LLM HTTP retries remain separately
bounded; an execution attempt is not the same unit as an upstream HTTP call.
Admission endpoints share their API-key bucket and fail closed when Redis is down.

## Consequences and alternatives

- Synchronous `/ask` remains useful, but is not a durable queue or a guarantee
  against user-visible provider errors. Persistent outages exhaust retry budgets.
- A simple in-process background task would not provide the same cross-process
  storage/ownership semantics. A larger broker/workflow system would add MVP overhead.
- Priority is derived from authenticated role, not a caller field. Sustained
  high-priority traffic can delay default work; this is not a fairness guarantee.
- Ownership hashes are pseudonyms, not anonymity. No raw API key belongs in Redis.
- Worker registration/heartbeat health is bounded and can be stale after abrupt
  restarts. An unhealthy running container does not automatically restart itself.

## Evidence

- [Job storage/API](../../../src/app/queue/jobs.py), [worker policy](../../../src/app/queue/worker.py), [token buckets](../../../src/app/queue/limits.py).
- [Queue policy tests](../../../tests/unit/test_queue_policy.py), [HTTP ownership/masking tests](../../../tests/api/test_jobs.py).
- [Real Redis/RQ tests](../../../tests/integration/test_worker.py), [T-041 regression evidence](../../09-testing/evidence/T-041-regression-summary.json).
