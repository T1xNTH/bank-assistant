---
id: development-overview
title: Development
type: reference
domain: development
module: repository
tags: [development, standards, workflow]
priority: 3
---
# Phát triển

Phần này cung cấp hướng dẫn phát triển, chuẩn viết code và công cụ.

## Nội dung
- `agent-cli.md` – CLI `scripts/agent` quản lý lifecycle task/review/QA/epic
- `team-workflow.md` – Quy trình làm việc của team 2 người
- `coding-standards.md` – Quy ước viết code
- `tooling.md` – Công cụ phát triển và cách cài đặt
- `corpus.md` – Dựng lại bộ tài liệu `data/` theo manifest, quy ước `superseded_by`
- `workflow.md` – Git workflow và quy trình PR
- `ci.md` – CI quality gate, chạy Docker stack và smoke test API; giới hạn kiểm tra UI hiện tại
- [Qdrant store](qdrant-store.md) - T009 input format, identity and real-server checks.
- `ingest.md` – Chạy `scripts/ingest.py` nạp bộ tài liệu vào Qdrant, cache parse/embed
- `retrieve.md` – `retrieve()`: mode dense và hybrid (RRF), bộ lọc phòng ban và văn bản bị thay thế
- `rerank.md` – Rerank bge-reranker-v2-m3, ngưỡng từ chối `REFUSAL_THRESHOLD`, số ứng viên `RERANK_CANDIDATES`
- [LLM gateway](llm-gateway.md) - LiteLLM aliases, OpenAI setup, optional Ollama and smoke checks.
- [Request audit](audit.md) - SQLite rows, privacy fallback, persistence and failure behavior.
