---
id: task-board
title: Task Board
type: execution
domain: governance
module: execution
tags: [tasks, execution, board]
priority: 1
---
# Task Board

## Purpose

Maintain the authoritative registry of executable tasks and their lifecycle state.

## Status Model

- **Valid Statuses**: `pending | in-progress | blocked | review | done | cancelled`
- `pending -> in-progress` requires an owner, sufficient context, satisfied dependencies, and parent epic `EPIC_IN_PROGRESS`.
- `in-progress -> blocked` requires a linked blocker.
- `in-progress -> review` requires implementation evidence and acceptance-criteria results.
- `review -> done` requires required review and QA evidence.
- `blocked -> in-progress` requires verified blocker resolution.
- `cancelled` requires an authorized rationale; `done` and `cancelled` are terminal.

## Task Records

| Task ID | Epic ID | Title | Owner | Status | Dependencies | Blocker IDs | Evidence Links | Updated Date |
|---|---|---|---|---|---|---|---|---|
| `T-001` | `E-001` | `Cross-review and approve SRS, contract, architecture (DEC-001)` | `trong-hung` | `pending` | `none` | `none` | `.agent/execution/tasks/T-001.md` | `2026-10-24` |
| `T-002` | `E-001` | `Confirm contracts.py and fakes cover platform needs` | `teammate-b` | `pending` | `T-001` | `none` | `.agent/execution/tasks/T-002.md` | `2026-10-24` |
| `T-003` | `E-002` | `Install Docker on both machines; core stack healthy` | `teammate-b` | `pending` | `none` | `none` | `.agent/execution/tasks/T-003.md` | `2026-10-24` |
| `T-004` | `E-002` | `API foundation: error envelope, request id, structured logging` | `teammate-b` | `pending` | `T-003` | `none` | `.agent/execution/tasks/T-004.md` | `2026-10-24` |
| `T-005` | `E-003` | `Collect 30 public PDFs and data/manifest.csv` | `trong-hung` | `pending` | `none` | `none` | `.agent/execution/tasks/T-005.md` | `2026-10-24` |
| `T-006` | `E-003` | `parse_docling: tables as Markdown, OCR (vi)` | `trong-hung` | `pending` | `none` | `none` | `.agent/execution/tasks/T-006.md` | `2026-10-24` |
| `T-007` | `E-003` | `chunk_pages: recursive + table-aware chunks` | `trong-hung` | `pending` | `T-006` | `none` | `.agent/execution/tasks/T-007.md` | `2026-10-24` |
| `T-008` | `E-003` | `embed: bge-m3 dense + sparse` | `trong-hung` | `pending` | `none` | `none` | `.agent/execution/tasks/T-008.md` | `2026-10-24` |
| `T-009` | `E-003` | `store: Qdrant collection, payload indexes, upsert` | `trong-hung` | `pending` | `T-003` | `none` | `.agent/execution/tasks/T-009.md` | `2026-10-24` |
| `T-010` | `E-003` | `scripts/ingest.py end-to-end on the corpus` | `trong-hung` | `pending` | `T-005, T-007, T-008, T-009` | `none` | `.agent/execution/tasks/T-010.md` | `2026-10-24` |
| `T-011` | `E-005` | `LiteLLM + Ollama services and aliases` | `teammate-b` | `pending` | `T-003` | `none` | `.agent/execution/tasks/T-011.md` | `2026-10-24` |
| `T-012` | `E-005` | `app/llm.py chat() via gateway with retry; LLM_BACKEND switch` | `teammate-b` | `pending` | `T-011` | `none` | `.agent/execution/tasks/T-012.md` | `2026-10-24` |
| `T-013` | `E-005` | `POST /chat with structured output` | `teammate-b` | `pending` | `T-012, T-004` | `none` | `.agent/execution/tasks/T-013.md` | `2026-10-24` |
| `T-014` | `E-006` | `auth: hashed API keys -> User, 401/403` | `teammate-b` | `pending` | `T-004` | `none` | `.agent/execution/tasks/T-014.md` | `2026-10-24` |
| `T-015` | `E-006` | `audit log in data/audit.db` | `teammate-b` | `pending` | `T-014` | `none` | `.agent/execution/tasks/T-015.md` | `2026-10-24` |
| `T-016` | `E-004` | `retrieve: dense, hybrid (RRF) modes` | `trong-hung` | `pending` | `T-010` | `none` | `.agent/execution/tasks/T-016.md` | `2026-10-24` |
| `T-017` | `E-004` | `rerank + REFUSAL_THRESHOLD` | `trong-hung` | `pending` | `T-016` | `none` | `.agent/execution/tasks/T-017.md` | `2026-10-24` |
| `T-018` | `E-004` | `prompts + RagAnswerer: citations and refusal` | `trong-hung` | `pending` | `T-017, T-012` | `none` | `.agent/execution/tasks/T-018.md` | `2026-10-24` |
| `T-019` | `E-004` | `Wire real RAG into /ask + integration test` | `trong-hung` | `pending` | `T-018, T-014` | `none` | `.agent/execution/tasks/T-019.md` | `2026-10-24` |
| `T-020` | `E-007` | `pii.py: Presidio + VN regex recognizers` | `teammate-b` | `pending` | `none` | `none` | `.agent/execution/tasks/T-020.md` | `2026-10-24` |
| `T-021` | `E-007` | `Mask input, output, logs, audit` | `teammate-b` | `pending` | `T-020, T-015` | `none` | `.agent/execution/tasks/T-021.md` | `2026-10-24` |
| `T-022` | `E-008` | `golden.jsonl: 50 questions (A 25 + B 25)` | `trong-hung` | `pending` | `T-010` | `none` | `.agent/execution/tasks/T-022.md` | `2026-10-24` |
| `T-023` | `E-008` | `Eval runner: RAGAS + hit@5 + refusal, 3 modes, report` | `trong-hung` | `pending` | `T-022, T-019` | `none` | `.agent/execution/tasks/T-023.md` | `2026-10-24` |
| `T-024` | `E-009` | `POST /ask/jobs + GET /ask/jobs/{id}` | `teammate-b` | `pending` | `T-021, T-003` | `none` | `.agent/execution/tasks/T-024.md` | `2026-10-24` |
| `T-025` | `E-009` | `Worker: rate limit, retry/backoff, priority, per-key limit` | `teammate-b` | `pending` | `T-024` | `none` | `.agent/execution/tasks/T-025.md` | `2026-10-24` |
