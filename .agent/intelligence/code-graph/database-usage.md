---
id: code-graph-database-usage
title: Code Graph Database Usage
type: intelligence
domain: database
module: code-graph
tags: [code-graph, database]
priority: 3
---
# Database Usage

Danh mục entity database, đường truy cập, migration và owner, dựa trên các nguồn được liên kết bên dưới.

## T-009 storage evidence

| Entity | Access | Owner | Sources |
|---|---|---|---|
| Qdrant bank_docs (or configured collection) | ensure_collection validates/creates dense1024/cosine + sparse; keyword indexes department/classification/superseded_by; upsert_chunks writes UUID5 doc/chunk identities in waited batches | trong-hung | src/app/rag/store.py; docs/05-database/schema.md; .agent/execution/tasks/T-009.md; .agent/reports/implementation/T-009.md |

Store does not implement retrieval/RBAC filtering. replace_document (1c46efa, PR38-F01) deletes a document's points that are not in its new chunk set. Integration test filters are verification, not a production retriever.
