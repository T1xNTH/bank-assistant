---
id: data-schema
title: Data Schema
type: reference
domain: database
module: storage
tags: [database, qdrant, sqlite]
priority: 2
---
# Data Schema

## Qdrant collection `bank_docs` (owner A)
Named vectors: `dense` (bge-m3, 1024, cosine), sparse `sparse` (bge-m3 lexical weights). One point per chunk.

| Payload field | Type | Required | Notes |
|---|---|---|---|
| `doc_id` | str | yes | stable id from `data/manifest.csv` |
| `source` | str | yes | file name shown in citations |
| `page` | int | yes | 1-based |
| `chunk_index` | int | yes | |
| `text` | str | yes | chunk text (tables as Markdown) |
| `department` | keyword | yes | `public`, `credit`, `hr` — payload index |
| `classification` | keyword | yes | `public`, `internal`, `confidential` — payload index |
| `effective_date` | date str | yes | ISO date |
| `superseded_by` | str \| null | yes | `doc_id` of the replacing document; non-null → excluded from retrieval |

`data/manifest.csv` columns: `doc_id,file,department,classification,effective_date,superseded_by,source_url`.

## SQLite
| File | Owner | Tables | Access |
|---|---|---|---|
| `data/audit.db` | B | `audit_log(ts, user_id, department, endpoint, question_masked, route, refused, latency_ms, cost_usd, trace_id)` | append only |
| `data/core_banking.db` | B | `accounts`, `transactions` (synthetic) | opened `mode=ro` by the agent |
| `data/tickets.db` | B | `tickets(id, created_by, summary, status, approved_by, ts)` | written only after approval |

## Redis (owner B)
RQ queues `ask-high`, `ask-default`; job payload contains masked question + `user_id` only; results TTL 1 h.

## Backup
Qdrant snapshots via `make backup` / `make restore` (FR-11).
