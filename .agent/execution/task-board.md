---
id: task-board
title: Task Board
type: execution
domain: governance
module: execution
tags: [tasks, execution, board]
priority: 1
---
# Bảng task (Task Board)

## Purpose

Lưu registry chính thức các task thực thi được và trạng thái lifecycle của chúng.

## Status Model

- **Valid Statuses**: `pending | in-progress | blocked | review | done | cancelled`
- `pending -> in-progress` cần có owner, đủ ngữ cảnh, dependency đã thoả và epic cha ở `EPIC_IN_PROGRESS`.
- `in-progress -> blocked` cần một blocker được liên kết.
- `in-progress -> review` cần bằng chứng hiện thực và kết quả acceptance criteria.
- `review -> done` cần bằng chứng review và QA bắt buộc.
- `blocked -> in-progress` cần blocker đã được giải quyết và kiểm chứng.
- `cancelled` cần lý do được phép; `done` và `cancelled` là trạng thái kết thúc.

## Task Records

| Task ID | Epic ID | Tiêu đề | Owner | Trạng thái | Phụ thuộc | Blocker IDs | Link bằng chứng | Ngày cập nhật |
|---|---|---|---|---|---|---|---|---|
| `T-001` | `E-001` | `Review chéo và duyệt SRS, contract, kiến trúc (DEC-001)` | `trong-hung` | `done` | `none` | `none` | `.agent/execution/tasks/T-001.md, .agent/reports/implementation/T-001.md, .agent/reports/review/T-001.md, .agent/reports/qa/T-001.md` | `2026-10-27` |
| `T-002` | `E-001` | `Xác nhận contracts.py và fakes đáp ứng nhu cầu phía nền tảng` | `teammate-b` | `review` | `T-001` | `none` | `.agent/execution/tasks/T-002.md, .agent/reports/implementation/T-002.md, .agent/reports/review/T-002.md, .agent/reports/qa/T-002.md` | `2026-10-27` |
| `T-003` | `E-002` | `Cài Docker trên cả hai máy; stack lõi healthy` | `teammate-b` | `done` | `none` | `none` | `.agent/execution/tasks/T-003.md, .agent/reports/implementation/T-003.md, .agent/reports/review/T-003.md, .agent/reports/qa/T-003.md` | `2026-10-27` |
| `T-004` | `E-002` | `Nền tảng API: định dạng lỗi chung, request id, structured logging` | `teammate-b` | `done` | `T-003` | `none` | `.agent/execution/tasks/T-004.md, .agent/reports/implementation/T-004.md, .agent/reports/review/T-004.md, .agent/reports/qa/T-004.md, .agent/reports/implementation/T-004-followup.md, .agent/reports/review/T-004-followup.md, .agent/reports/qa/T-004-followup.md, .agent/reports/implementation/T-004-ci-runtime.md` | `2026-10-29` |
| `T-005` | `E-003` | `Thu thập 30 PDF công khai và data/manifest.csv` | `trong-hung` | `done` | `none` | `none` | `.agent/execution/tasks/T-005.md, .agent/reports/implementation/T-005.md, .agent/reports/review/T-005.md` | `2026-10-28` |
| `T-006` | `E-003` | `parse_docling: bảng dạng Markdown, OCR (vi)` | `trong-hung` | `done` | `none` | `none` | `.agent/execution/tasks/T-006.md, .agent/reports/implementation/T-006.md, .agent/reports/review/T-006.md, .agent/reports/implementation/T-006-PR30-final-fixes.md` | `2026-10-29` |
| `T-007` | `E-003` | `chunk_pages: chunk đệ quy + nhận biết bảng` | `trong-hung` | `done` | `T-006` | `none` | `.agent/execution/tasks/T-007.md, .agent/reports/implementation/T-007.md, .agent/reports/review/T-007.md, .agent/reports/implementation/T-007-PR35-F01.md` | `2026-10-29` |
| `T-008` | `E-003` | `embed: bge-m3 dense + sparse` | `trong-hung` | `done` | `none` | `none` | `.agent/execution/tasks/T-008.md, .agent/reports/implementation/T-008.md, .agent/reports/review/T-008.md` | `2026-10-28` |
| `T-009` | `E-003` | `store: Qdrant collection, payload index, upsert` | `trong-hung` | `done` | `T-003` | `none` | `.agent/execution/tasks/T-009.md, .agent/reports/implementation/T-009.md, .agent/reports/review/T-009.md` | `2026-10-29` |
| `T-010` | `E-003` | `scripts/ingest.py chạy end-to-end trên bộ tài liệu` | `trong-hung` | `review` | `T-005, T-007, T-008, T-009` | `none` | `.agent/execution/tasks/T-010.md, .agent/reports/implementation/T-010.md, .agent/reports/review/T-010.md` | `2026-10-29` |
| `T-011` | `E-005` | `Service LiteLLM + Ollama và các alias` | `teammate-b` | `review` | `T-003` | `none` | `.agent/execution/tasks/T-011.md, .agent/reports/implementation/T-011.md, .agent/reports/implementation/T-011-openai.md` | `2026-10-29` |
| `T-012` | `E-005` | `app/llm.py chat() qua gateway có retry; công tắc LLM_BACKEND` | `teammate-b` | `review` | `T-011` | `none` | `.agent/execution/tasks/T-012.md, .agent/reports/implementation/T-012.md` | `2026-10-29` |
| `T-013` | `E-005` | `POST /chat với output có cấu trúc` | `teammate-b` | `pending` | `T-012, T-004` | `none` | `.agent/execution/tasks/T-013.md` | `2026-10-24` |
| `T-014` | `E-006` | `auth: API key đã hash -> User, 401/403` | `teammate-b` | `review` | `T-004` | `none` | `.agent/execution/tasks/T-014.md, .agent/reports/implementation/T-014.md, .agent/reports/review/T-014.md, .agent/reports/review/T-014-round-2.md, .agent/reports/review/T-014-claude-pr49.md, .agent/reports/implementation/T-014-PR49-resolution.md` | `2026-10-29` |
| `T-015` | `E-006` | `audit log trong data/audit.db` | `teammate-b` | `pending` | `T-014` | `none` | `.agent/execution/tasks/T-015.md` | `2026-10-24` |
| `T-016` | `E-004` | `retrieve: các mode dense, hybrid (RRF)` | `trong-hung` | `pending` | `T-010` | `none` | `.agent/execution/tasks/T-016.md` | `2026-10-24` |
| `T-017` | `E-004` | `rerank + REFUSAL_THRESHOLD` | `trong-hung` | `pending` | `T-016` | `none` | `.agent/execution/tasks/T-017.md` | `2026-10-24` |
| `T-018` | `E-004` | `prompts + RagAnswerer: trích dẫn và từ chối` | `trong-hung` | `pending` | `T-017, T-012` | `none` | `.agent/execution/tasks/T-018.md` | `2026-10-24` |
| `T-019` | `E-004` | `Nối RAG thật vào /ask + integration test` | `trong-hung` | `pending` | `T-018, T-014` | `none` | `.agent/execution/tasks/T-019.md` | `2026-10-24` |
| `T-020` | `E-007` | `pii.py: Presidio + regex recognizer cho VN` | `teammate-b` | `pending` | `none` | `none` | `.agent/execution/tasks/T-020.md` | `2026-10-24` |
| `T-021` | `E-007` | `Che input, output, log, audit` | `teammate-b` | `pending` | `T-020, T-015` | `none` | `.agent/execution/tasks/T-021.md` | `2026-10-24` |
| `T-022` | `E-008` | `golden.jsonl: 50 câu hỏi (A 25 + B 25)` | `trong-hung` | `pending` | `T-010` | `none` | `.agent/execution/tasks/T-022.md` | `2026-10-24` |
| `T-023` | `E-008` | `Eval runner: RAGAS + hit@5 + từ chối, 3 mode, báo cáo` | `trong-hung` | `pending` | `T-022, T-019` | `none` | `.agent/execution/tasks/T-023.md` | `2026-10-24` |
| `T-024` | `E-009` | `POST /ask/jobs + GET /ask/jobs/{id}` | `teammate-b` | `pending` | `T-021, T-003` | `none` | `.agent/execution/tasks/T-024.md` | `2026-10-24` |
| `T-025` | `E-009` | `Worker: rate limit, retry/backoff, priority, giới hạn theo key` | `teammate-b` | `pending` | `T-024` | `none` | `.agent/execution/tasks/T-025.md` | `2026-10-24` |
