---
id: data-schema
title: Data Schema
type: reference
domain: database
module: storage
tags: [database, qdrant, sqlite]
priority: 2
---
# Schema dữ liệu

## Qdrant collection `bank_docs` (owner A)
Named vector: `dense` (bge-m3, 1024, cosine), sparse `sparse` (trọng số lexical của bge-m3). Mỗi chunk là một point.

| Trường payload | Kiểu | Bắt buộc | Ghi chú |
|---|---|---|---|
| `doc_id` | str | có | id ổn định lấy từ `data/manifest.csv` |
| `source` | str | có | tên file hiển thị trong trích dẫn |
| `page` | int | có | đánh số từ 1 |
| `chunk_index` | int | có | |
| `text` | str | có | nội dung chunk (bảng ở dạng Markdown) |
| `department` | keyword | có | `public`, `credit`, `hr` — có payload index |
| `classification` | keyword | có | `public`, `internal`, `confidential` — có payload index |
| `effective_date` | date str | có | ngày ISO |
| `superseded_by` | str \| null | có | `doc_id` của tài liệu thay thế; khác null → bị loại khỏi retrieval |

Các cột của `data/manifest.csv`: `doc_id,file,department,classification,effective_date,superseded_by,source_url`.

## SQLite
| File | Owner | Bảng | Truy cập |
|---|---|---|---|
| `data/audit.db` | B | `audit_log(ts, user_id, department, endpoint, question_masked, route, refused, latency_ms, cost_usd, trace_id)` | chỉ append |
| `data/core_banking.db` | B | `accounts`, `transactions` (dữ liệu tổng hợp) | agent mở với `mode=ro` |
| `data/tickets.db` | B | `tickets(id, created_by, summary, status, approved_by, ts)` | chỉ ghi sau khi được duyệt |

## Redis (owner B)
Hàng chờ RQ `ask-high`, `ask-default`; payload của job chỉ chứa câu hỏi đã che + `user_id`; kết quả có TTL 1 h.

## Backup
Snapshot Qdrant qua `make backup` / `make restore` (FR-11).
