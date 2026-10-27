---
id: epics-v1
title: Epics
type: planning
domain: governance
module: planning
tags: [epics, planning]
priority: 2
---
# Epics

## Purpose

Lưu registry chính thức các kết quả bàn giao có giới hạn rõ, có thể được tách thành các task thực thi được.

## Status Model

- **Valid Statuses**: `EPIC_PROPOSED | EPIC_READY | EPIC_IN_PROGRESS | EPIC_BLOCKED | EPIC_DONE | EPIC_CANCELLED`

## Epic Records

| Epic ID | Milestone ID | Kết quả | Owner | Trạng thái | Task IDs | Bằng chứng nghiệm thu | Governance links |
|---|---|---|---|---|---|---|---|

| `E-001` | `M-001` | `Baseline SRS, contract, kiến trúc; src/app/contracts.py + tests/fakes.py` | `trong-hung` | `EPIC_IN_PROGRESS` | `T-001, T-002` | `pending` | `.agent/governance/decisions/DEC-001.md` |
| `E-002` | `M-001` | `Nền tảng: Docker, compose (api, qdrant, redis), job CI check, branch protection` | `teammate-b` | `EPIC_IN_PROGRESS` | `T-003, T-004` | `pending` | `.agent/governance/decisions/DEC-001.md` |
| `E-003` | `M-001` | `FR-01 ingest: docling -> chunk -> bge-m3 dense+sparse -> Qdrant với đủ payload; 30 PDF + manifest` | `trong-hung` | `EPIC_READY` | `T-005, T-006, T-007, T-008, T-009, T-010` | `pending` | `.agent/governance/decisions/DEC-001.md` |
| `E-004` | `M-001` | `FR-02 retrieval + /ask: hybrid RRF, rerank, trích dẫn, ngưỡng từ chối` | `trong-hung` | `EPIC_READY` | `T-016, T-017, T-018, T-019` | `pending` | `.agent/governance/decisions/DEC-001.md` |
| `E-005` | `M-001` | `FR-04a LLM gateway: LiteLLM + Ollama, llm.chat(), alias` | `teammate-b` | `EPIC_READY` | `T-011, T-012, T-013` | `pending` | `.agent/governance/decisions/DEC-001.md` |
| `E-006` | `M-001` | `FR-05 xác thực (API key đã hash -> User), mô hình RBAC, audit log` | `teammate-b` | `EPIC_READY` | `T-014, T-015` | `pending` | `.agent/governance/decisions/DEC-001.md` |
| `E-007` | `M-001` | `FR-06 che PII ở input, output, log, trace, hàng chờ` | `teammate-b` | `EPIC_READY` | `T-020, T-021` | `pending` | `.agent/governance/decisions/DEC-001.md` |
| `E-008` | `M-001` | `FR-03 eval: golden set 50 câu, RAGAS, 3 mode, báo cáo, ngưỡng` | `trong-hung` | `EPIC_READY` | `T-022, T-023` | `pending` | `.agent/governance/decisions/DEC-001.md` |
| `E-009` | `M-001` | `FR-09 hàng chờ job: /ask/jobs, worker giới hạn tốc độ, retry/backoff, priority, 503, giới hạn theo key` | `teammate-b` | `EPIC_READY` | `T-024, T-025` | `pending` | `.agent/governance/decisions/DEC-001.md` |
| `E-010` | `M-002` | `FR-04b + FR-02: route nội dung nhạy cảm sang local, RBAC filter trong retrieve, lọc tài liệu bị thay thế` | `trong-hung` | `EPIC_PROPOSED` | `none` | `pending` | `.agent/governance/decisions/DEC-001.md` |
| `E-011` | `M-002` | `FR-07 agent: LangGraph, 3 tool, HITL interrupt, SQLite chỉ đọc, các endpoint /agent` | `trong-hung` | `EPIC_PROPOSED` | `none` | `pending` | `.agent/governance/decisions/DEC-001.md` |
| `E-012` | `M-002` | `FR-08 n8n: tiếp nhận -> phân loại -> /ask -> duyệt -> phản hồi; workflow xử lý lỗi` | `teammate-b` | `EPIC_PROPOSED` | `none` | `pending` | `.agent/governance/decisions/DEC-001.md` |
| `E-013` | `M-002` | `FR-10 observability: trace Langfuse, token, chi phí, p95, thời gian chờ; /feedback` | `teammate-b` | `EPIC_PROPOSED` | `none` | `pending` | `.agent/governance/decisions/DEC-001.md` |
| `E-014` | `M-002` | `Vòng cải tiến chất lượng: sửa 3 câu trả lời tệ nhất từ trace, chạy lại eval để đạt NFR-01..04` | `trong-hung` | `EPIC_PROPOSED` | `none` | `pending` | `.agent/governance/decisions/DEC-001.md` |
| `E-015` | `M-002` | `FR-11 release hardening: CI eval gate, trivy, compose profiles, backup Qdrant, test clone sạch` | `teammate-b` | `EPIC_PROPOSED` | `none` | `pending` | `.agent/governance/decisions/DEC-001.md` |
| `E-016` | `M-002` | `FR-12 UI demo (Streamlit) + README + ADR` | `trong-hung` | `EPIC_PROPOSED` | `none` | `pending` | `.agent/governance/decisions/DEC-001.md` |
