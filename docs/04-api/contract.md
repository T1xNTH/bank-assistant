---
id: project-contract
title: API Contract — bank-assistant v0
type: reference
domain: api
module: repository
tags: [contract, api, openapi]
priority: 1
---
# API Contract — bank-assistant v0

## Input Status

- **Status**: `ingested`
- **Authority**: `draft — pending approval in DEC-001`
- **Source Artifact**: `docs/04-api/openapi.yaml`
- **Ingested Date**: `2026-10-24`
- **Validated By**: `trong-hung`, `teammate-b`

## Scope

The external HTTP contract of the API service and the internal Python contracts (`src/app/contracts.py`) that let the two owners work in parallel. The machine-readable source of truth is `docs/04-api/openapi.yaml`; this page explains rules that a schema cannot express.

## Endpoints

| Method | Path | Auth | Owner | Summary |
|---|---|---|---|---|
| GET | `/health` | none | B | Liveness |
| POST | `/chat` | key | B | Free chat with structured output (intent, needs_human) |
| POST | `/ask` | key | A | Synchronous RAG answer with citations |
| POST | `/ask/jobs` | key | B | Enqueue an `/ask` request → `202 {job_id, position}` |
| GET | `/ask/jobs/{job_id}` | key (owner only) | B | `queued | running | done | failed` + result |
| POST | `/agent` | key | A | Start/continue an agent thread |
| POST | `/agent/{thread_id}/decision` | key, role `approver` | B | Approve/reject a pending action |
| POST | `/feedback` | key | B | 👍/👎 on a `trace_id` |

## Rules

- **Authentication**: header `X-API-Key`. Keys are stored hashed (`config/api_keys.json`); a key maps to `User(user_id, department, role)`.
- **Errors**: JSON `{"error": {"code": str, "message": str}}` with
  `400` invalid body, `401` missing/invalid key, `403` RBAC/role denied, `404` unknown job/thread, `409` decision already taken, `429` per-key rate limit (with `Retry-After`), `503` queue full or dependency down.
- **Refusal** is not an error: `200` with `found: false` and `answer` = `REFUSAL` constant (`"Không tìm thấy thông tin này trong tài liệu nội bộ hiện có."`).
- **Citations**: every `found: true` answer has ≥ 1 citation `{n, source, page, score}`; `n` matches `[n]` markers in the answer.
- **PII**: request text is masked before it is logged, traced or enqueued; responses are masked on output.
- **Versioning**: additive changes (new optional fields) bump `info.version` minor; removing/renaming fields or changing semantics needs an approved change request and a major bump.

## Internal Contracts (`src/app/contracts.py`)

| Contract | Signature | Producer | Consumers | Fake |
|---|---|---|---|---|
| `LLM` | `chat(messages, alias, temperature=0.0) -> LLMResult` | B (`app/llm.py`) | A (answer, agent) | `tests/fakes.py::FakeLLM` |
| `Retriever` | `retrieve(question, user, k) -> list[Hit]` | A (`app/rag/retrieve.py`) | A answer, B API | `FakeRetriever` |
| `Answerer` | `answer(question, user, mode=None) -> AskResult` | A (`app/rag/answer.py`) | B API + worker | `FakeAnswerer` |
| `Masker` | `mask_text(text) -> tuple[str, list[str]]` | B (`app/security/pii.py`) | A + B | `FakeMasker` |
| `User` | dataclass `user_id, department, role` | B (`app/security/auth.py`) | all | — |

Backend selection at runtime: `RAG_BACKEND=fake|real`, `LLM_BACKEND=fake|litellm`.

## Change Control

Any change to `openapi.yaml` or `contracts.py` goes in its own PR, labelled `contract`, approved by both owners, and — once DEC-001 is accepted — backed by a change request in `.agent/governance/change-requests/`.

## Related Files

- `docs/04-api/openapi.yaml`
- `src/app/contracts.py`
- SRS: `docs/01-business/srs.md`

## Forbidden Actions

- Do not add endpoints or fields outside this contract without a change request.
- Do not return raw PII or chunks from departments the user cannot access.
