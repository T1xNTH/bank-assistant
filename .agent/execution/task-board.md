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
| `T-002` | `E-001` | `Xác nhận contracts.py và fakes đáp ứng nhu cầu phía nền tảng` | `teammate-b` | `done` | `T-001` | `none` | `.agent/execution/tasks/T-002.md, .agent/reports/implementation/T-002.md, .agent/reports/review/T-002.md, .agent/reports/qa/T-002.md` | `2026-11-02` |
| `T-003` | `E-002` | `Cài Docker trên cả hai máy; stack lõi healthy` | `teammate-b` | `done` | `none` | `none` | `.agent/execution/tasks/T-003.md, .agent/reports/implementation/T-003.md, .agent/reports/review/T-003.md, .agent/reports/qa/T-003.md` | `2026-10-27` |
| `T-004` | `E-002` | `Nền tảng API: định dạng lỗi chung, request id, structured logging` | `teammate-b` | `done` | `T-003` | `none` | `.agent/execution/tasks/T-004.md, .agent/reports/implementation/T-004.md, .agent/reports/review/T-004.md, .agent/reports/qa/T-004.md, .agent/reports/implementation/T-004-followup.md, .agent/reports/review/T-004-followup.md, .agent/reports/qa/T-004-followup.md, .agent/reports/implementation/T-004-ci-runtime.md` | `2026-10-29` |
| `T-005` | `E-003` | `Thu thập 30 PDF công khai và data/manifest.csv` | `trong-hung` | `done` | `none` | `none` | `.agent/execution/tasks/T-005.md, .agent/reports/implementation/T-005.md, .agent/reports/review/T-005.md` | `2026-10-28` |
| `T-006` | `E-003` | `parse_docling: bảng dạng Markdown, OCR (vi)` | `trong-hung` | `done` | `none` | `none` | `.agent/execution/tasks/T-006.md, .agent/reports/implementation/T-006.md, .agent/reports/review/T-006.md, .agent/reports/implementation/T-006-PR30-final-fixes.md` | `2026-10-29` |
| `T-007` | `E-003` | `chunk_pages: chunk đệ quy + nhận biết bảng` | `trong-hung` | `done` | `T-006` | `none` | `.agent/execution/tasks/T-007.md, .agent/reports/implementation/T-007.md, .agent/reports/review/T-007.md, .agent/reports/implementation/T-007-PR35-F01.md` | `2026-10-29` |
| `T-008` | `E-003` | `embed: bge-m3 dense + sparse` | `trong-hung` | `done` | `none` | `none` | `.agent/execution/tasks/T-008.md, .agent/reports/implementation/T-008.md, .agent/reports/review/T-008.md` | `2026-10-28` |
| `T-009` | `E-003` | `store: Qdrant collection, payload index, upsert` | `trong-hung` | `done` | `T-003` | `none` | `.agent/execution/tasks/T-009.md, .agent/reports/implementation/T-009.md, .agent/reports/review/T-009.md` | `2026-10-29` |
| `T-010` | `E-003` | `scripts/ingest.py chạy end-to-end trên bộ tài liệu` | `trong-hung` | `done` | `T-005, T-007, T-008, T-009` | `none` | `.agent/execution/tasks/T-010.md, .agent/reports/implementation/T-010.md, .agent/reports/review/T-010.md` | `2026-10-29` |
| `T-011` | `E-005` | `Service LiteLLM + Ollama và các alias` | `teammate-b` | `done` | `T-003` | `none` | `.agent/execution/tasks/T-011.md, .agent/reports/implementation/T-011.md, .agent/reports/implementation/T-011-openai.md, .agent/reports/review/T-011.md` | `2026-10-29` |
| `T-012` | `E-005` | `app/llm.py chat() qua gateway có retry; công tắc LLM_BACKEND` | `teammate-b` | `done` | `T-011` | `none` | `.agent/execution/tasks/T-012.md, .agent/reports/implementation/T-012.md, .agent/reports/review/T-012.md` | `2026-10-30` |
| `T-013` | `E-005` | `POST /chat với output có cấu trúc` | `teammate-b` | `done` | `T-012, T-004` | `none` | `.agent/execution/tasks/T-013.md, .agent/reports/implementation/T-013.md, .agent/reports/implementation/T-013-PR55-fixes.md, .agent/reports/review/T-013.md` | `2026-11-02` |
| `T-014` | `E-006` | `auth: API key đã hash -> User, 401/403` | `teammate-b` | `done` | `T-004` | `none` | `.agent/execution/tasks/T-014.md, .agent/reports/implementation/T-014.md, .agent/reports/review/T-014.md, .agent/reports/review/T-014-round-2.md, .agent/reports/review/T-014-claude-pr49.md, .agent/reports/implementation/T-014-PR49-resolution.md, .agent/reports/implementation/T-014-closure.md` | `2026-10-30` |
| `T-015` | `E-006` | `audit log trong data/audit.db` | `teammate-b` | `done` | `T-014` | `none` | `.agent/execution/tasks/T-015.md, .agent/reports/implementation/T-015.md, .agent/reports/implementation/T-015-PR56-resolution.md, .agent/reports/implementation/T-021-dependency-closure.md` | `2026-10-30` |
| `T-016` | `E-004` | `retrieve: các mode dense, hybrid (RRF)` | `trong-hung` | `done` | `T-010` | `none` | `.agent/execution/tasks/T-016.md, .agent/reports/implementation/T-016.md, .agent/reports/review/T-016.md, .agent/reports/qa/E-004-T016.md` | `2026-10-30` |
| `T-017` | `E-004` | `rerank + REFUSAL_THRESHOLD` | `trong-hung` | `done` | `T-016` | `none` | `.agent/execution/tasks/T-017.md, .agent/reports/implementation/T-017.md, .agent/reports/review/T-017.md` | `2026-10-30` |
| `T-018` | `E-004` | `prompts + RagAnswerer: trích dẫn và từ chối` | `trong-hung` | `done` | `T-017, T-012` | `none` | `.agent/execution/tasks/T-018.md, .agent/reports/implementation/T-018.md, .agent/reports/review/T-018.md` | `2026-10-31` |
| `T-019` | `E-004` | `Nối RAG thật vào /ask + integration test` | `trong-hung` | `done` | `T-018, T-014` | `none` | `.agent/execution/tasks/T-019.md, .agent/reports/implementation/T-019.md, .agent/reports/review/T-019.md` | `2026-10-31` |
| `T-020` | `E-007` | `pii.py: Presidio + regex recognizer cho VN` | `teammate-b` | `done` | `none` | `none` | `.agent/execution/tasks/T-020.md, .agent/reports/implementation/T-020.md, .agent/reports/review/T-020.md, .agent/governance/issues/ISSUE-021.md, .agent/reports/implementation/T-020-F01.md, .agent/reports/review/T-020-F01.md, .agent/reports/implementation/T-020-PR58-resolution.md, .agent/reports/implementation/T-020-PR58-fixes.md, .agent/reports/review/T-020-claude-pr58.md, .agent/reports/implementation/T-020-PR58-round-2-fixes.md, .agent/reports/review/T-020-claude-pr58-round-2.md, .agent/reports/implementation/T-020-PR58-round-3-fixes.md, .agent/reports/review/T-020-claude-pr58-round-3.md, .agent/reports/implementation/T-021-dependency-closure.md` | `2026-10-30` |
| `T-021` | `E-007` | `Che input, output, log, audit` | `teammate-b` | `done` | `T-020, T-015` | `none` | `.agent/execution/tasks/T-021.md, .agent/reports/implementation/T-021.md, .agent/reports/implementation/T-021-PR61-followup.md, .agent/reports/implementation/T-021-PR61-cleanup.md, .agent/reports/implementation/T-021-PR61-merge-main.md, .agent/reports/implementation/T-024-dependency-closure.md` | `2026-10-30` |
| `T-022` | `E-008` | `golden.jsonl: 50 câu hỏi (A 25 + B 25)` | `trong-hung` | `done` | `T-010` | `none` | `.agent/execution/tasks/T-022.md, .agent/reports/implementation/T-022.md, .agent/reports/implementation/T-022-PR60-fixes.md` | `2026-10-31` |
| `T-023` | `E-008` | `Eval runner: RAGAS + hit@5 + từ chối, 3 mode, báo cáo` | `trong-hung` | `done` | `T-022, T-019` | `none` | `.agent/execution/tasks/T-023.md, .agent/reports/implementation/T-023.md, .agent/reports/review/T-023.md` | `2026-11-02` |
| `T-024` | `E-009` | `POST /ask/jobs + GET /ask/jobs/{id}` | `teammate-b` | `done` | `T-021, T-003` | `none` | `.agent/execution/tasks/T-024.md, .agent/reports/implementation/T-024.md, .agent/reports/implementation/T-025-dependency-closure.md` | `2026-10-31` |
| `T-025` | `E-009` | `Worker: rate limit, retry/backoff, priority, giới hạn theo key` | `teammate-b` | `done` | `T-024` | `none` | `.agent/execution/tasks/T-025.md, .agent/reports/implementation/T-025.md, .agent/reports/review/T-025.md` | `2026-11-02` |
| `T-026` | `E-010` | `decide_route: PII hoặc chunk confidential -> local-chat; nối vào /ask và worker` | `trong-hung` | `done` | `none` | `none` | `.agent/execution/tasks/T-026.md, .agent/reports/implementation/T-026.md, .agent/reports/review/T-026.md, .agent/reports/qa/E-010-T026.md` | `2026-11-02` |
| `T-027` | `E-010` | `Nhãn classification cho corpus + test rò RBAC và tài liệu bị thay thế trên Qdrant thật` | `trong-hung` | `review` | `T-026` | `none` | `.agent/execution/tasks/T-027.md, .agent/reports/implementation/T-027.md, .agent/reports/implementation/T-027-PR93-fixes.md` | `2026-11-02` |
| `T-028` | `E-011` | `SQLite tổng hợp core_banking (mode=ro) + tickets store chỉ ghi sau khi duyệt` | `teammate-b` | `done` | `none` | `none` | `.agent/execution/tasks/T-028.md, .agent/reports/implementation/T-028.md, .agent/reports/implementation/T-028-PR87-fixes.md, .agent/reports/implementation/T-029-dependency-closure.md` | `2026-11-02` |
| `T-029` | `E-011` | `loan.py tinh_lai_vay + 3 tool gắn với user hiện tại` | `trong-hung` | `done` | `T-028` | `none` | `.agent/execution/tasks/T-029.md, .agent/reports/implementation/T-029.md, .agent/reports/review/T-029.md` | `2026-11-02` |
| `T-030` | `E-011` | `LangGraph agent: chọn RAG hoặc tool, interrupt trước tao_ticket, checkpointer` | `trong-hung` | `done` | `T-029` | `none` | `.agent/execution/tasks/T-030.md, .agent/reports/implementation/T-030.md, .agent/reports/review/T-030.md` | `2026-11-03` |
| `T-031` | `E-011` | `POST /agent và POST /agent/{thread_id}/decision (chỉ approver, 409 khi đã quyết)` | `teammate-b` | `done` | `T-030` | `none` | `.agent/execution/tasks/T-031.md, .agent/reports/implementation/T-031.md, .agent/reports/review/T-031.md, .agent/reports/implementation/T-031-handoff.md` | `2026-11-03` |
| `T-032` | `E-012` | `Prompt phân loại intent/needs_human cho n8n + bộ 20 mẫu kiểm` | `trong-hung` | `done` | `none` | `none` | `.agent/execution/tasks/T-032.md, .agent/reports/implementation/T-032.md, .agent/reports/review/T-032.md` | `2026-11-03` |
| `T-033` | `E-012` | `n8n + Mailpit (profile automation) và workflow intake-to-reply` | `teammate-b` | `done` | `T-032` | `none` | `.agent/execution/tasks/T-033.md, .agent/reports/implementation/T-033.md, .agent/reports/implementation/T-033-PR98-fixes.md, .agent/governance/issues/ISSUE-029.md` | `2026-11-03` |
| `T-034` | `E-012` | `Workflow error-handler + tài liệu vận hành n8n` | `teammate-b` | `done` | `T-033` | `none` | `.agent/execution/tasks/T-034.md, .agent/reports/implementation/T-034.md, .agent/reports/implementation/T-034-PR101-fixes.md, .agent/governance/issues/ISSUE-030.md` | `2026-11-04` |
| `T-035` | `E-013` | `Langfuse (profile obs) + tracing.py cho /ask, /chat, worker (chờ vs xử lý)` | `teammate-b` | `done` | `none` | `none` | `.agent/execution/tasks/T-035.md, .agent/reports/implementation/T-035.md, .agent/reports/implementation/T-035-review-followup.md, .agent/reports/qa/T-035-recheck.md, .agent/reports/review/T-035.md` | `2026-11-03` |
| `T-036` | `E-013` | `llm_cost.cost_of + token/chi phí mỗi request vào trace và audit; POST /feedback` | `teammate-b` | `review` | `T-035` | `none` | `.agent/execution/tasks/T-036.md, .agent/reports/implementation/T-036.md` | `2026-11-04` |
| `T-037` | `E-013` | `Sửa ISSUE-027 (rate limit theo key /chat, /ask) và ISSUE-028 (audit /chat)` | `teammate-b` | `review` | `none` | `none` | `.agent/execution/tasks/T-037.md, .agent/reports/implementation/T-037.md, .agent/reports/implementation/T-037-PR102-followup.md, .agent/reports/review/T-037.md` | `2026-11-04` |
| `T-038` | `E-014` | `Sửa 3 câu trả lời tệ nhất từ trace/eval, chạy lại eval 3 mode` | `trong-hung` | `done` | `T-035, T-026` | `none` | `.agent/execution/tasks/T-038.md, .agent/reports/implementation/T-038.md, .agent/reports/review/T-038.md` | `2026-11-05` |
| `T-039` | `E-015` | `CI eval gate (10 câu) + trivy scan image` | `teammate-b` | `done` | `T-038` | `none` | `.agent/execution/tasks/T-039.md, .agent/reports/implementation/T-039.md` | `2026-11-05` |
| `T-040` | `E-015` | `Hoàn thiện compose profiles + make backup/restore Qdrant` | `teammate-b` | `done` | `T-035, T-033` | `none` | `.agent/execution/tasks/T-040.md, .agent/reports/implementation/T-040.md, .agent/reports/implementation/T-040-verification-retry.md, .agent/reports/review/T-040.md, .agent/reports/qa/T-040.md` | `2026-11-04` |
| `T-041` | `E-015` | `Test clone sạch -> make up healthy (NFR-10) và release QA v1.0-mvp` | `teammate-b` | `in-progress` | `T-039, T-040, T-031, T-034` | `none` | `.agent/execution/tasks/T-041.md, .agent/reports/implementation/T-041.md` | `2026-11-06` |
| `T-042` | `E-016` | `Streamlit UI: chọn role, chat /ask có trích dẫn, agent + duyệt` | `trong-hung` | `review` | `T-031` | `none` | `.agent/execution/tasks/T-042.md, .agent/reports/implementation/T-042.md, .agent/reports/review/T-042.md, .agent/reports/qa/T-042.md` | `2026-11-03` |
| `T-043` | `E-016` | `README tiếng Anh, cập nhật kiến trúc, ADR 0001–0004, kịch bản demo` | `trong-hung` | `pending` | `T-042` | `none` | `.agent/execution/tasks/T-043.md` | `2026-11-02` |
