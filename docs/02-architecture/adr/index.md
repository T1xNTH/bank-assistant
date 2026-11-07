---
id: architecture-adr-index
title: Implemented architecture decision records
type: reference
domain: architecture
module: repository
tags: [adr, architecture, t-043]
priority: 2
---
# Architecture decision records

These are retrospective records of the existing MVP implementation, not new
architecture approvals. T-043 review checks that they match source, requirements
and prior decisions. A future change still needs the applicable governance process.

| ADR | Existing decision | Primary evidence |
|---|---|---|
| [0001](0001-qdrant-hybrid.md) | Qdrant dense+sparse RRF with optional rerank | `src/app/rag/retrieve.py`, `tests/unit/test_retrieve.py` |
| [0002](0002-hybrid-model-routing.md) | Local-sensitive / eligible-cloud gateway routing | `src/app/routing.py`, `infrastructure/litellm/config.yaml` |
| [0003](0003-payload-rbac.md) | Trusted identity and query-time payload filters | `src/app/security/auth.py`, `src/app/rag/retrieve.py` |
| [0004](0004-rq-queue.md) | Redis/RQ async jobs with bounded retry and ownership | `src/app/queue/`, `tests/integration/test_worker.py` |
