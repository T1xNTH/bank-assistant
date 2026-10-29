---
id: qdrant-store-development
title: Qdrant storage and integration testing
type: reference
domain: rag
module: src/app/rag/store.py
tags: [qdrant, store, t-009, integration]
priority: 2
---
# Qdrant storage

`ensure_collection()` creates or verifies the configured collection (default `bank_docs`), with `dense` (1024, cosine), `sparse`, and keyword indexes on department, classification and superseded_by. Existing incompatible vectors or index types raise an error without deleting/recreating the collection. Compatible collections have missing indexes added. The SDK is pinned to the 1.12.x server series used in compose.

`upsert_chunks(chunks)` accepts flat dictionaries containing all nine payload fields from `docs/05-database/schema.md`, plus `dense` (1024 finite numbers) and `sparse` (`indices` and `values`, as returned by T-008 embed). Join the T-007 chunk metadata with the document manifest and embedding output before calling it. No embedding model or provider is loaded/called by the store. Missing security metadata is rejected; extra fields are omitted from payload. Text fields are stripped and must not be blank. Empty or blank manifest superseded_by values become null, so current documents match the null retrieval filter.

The point ID is UUID5 over a JSON tuple of application namespace, doc_id and chunk_index. Input order, source filename and text do not change identity. A repeat upsert replaces the same points; content changes at the same identity replace payload and vectors. Return value counts submitted chunks, including repeated IDs, rather than new points. Empty input returns zero without opening a connection. Input is fully validated before writes; batches of 64 wait for completion. A transport error can leave earlier batches committed, and replay converges to the same identities. `upsert_chunks` alone never removes obsolete chunks.

Ingest a whole document with `replace_document(doc_id, chunks)`. It upserts the chunks, then deletes the document's other points. Without this, a re-chunk that yields fewer chunks (for example re-ingesting `tt26-2021` with `superseded_by` set, ISSUE-010) would leave the old tail chunks with `superseded_by` null, still passing the retrieval filter. Every chunk must carry that `doc_id`; empty `chunks` removes the document. An interrupted call leaves a superset of the new chunks and replay converges. The delete filters on `doc_id` without a payload index, which is fine at corpus scale (30 documents).

Runtime configuration: `QDRANT_URL` (default localhost:6333), optional `QDRANT_API_KEY`, `QDRANT_COLLECTION` (default bank_docs). Inside compose, use `http://qdrant:6333`. Owned clients are closed; optional keyword arguments `client` and `collection` support reuse and isolation without changing existing no-argument calls.

Run `pytest tests/integration/test_store.py -m integration` against compose Qdrant 1.12.4. `QDRANT_TEST_URL` can target a separate local test instance. Tests fail if Qdrant is unavailable and use synthetic data in randomly named `test_bank_docs_*` collections, deleting only their own collections. They verify server-side index schemas, repeat upsert across batches, replacement, null filtering and non-destructive rejection of incompatible schemas. Unit tests use Qdrant local memory mode; its payload-index limitations are covered by the real-server tests.

Implementation references: [Qdrant vectors](https://qdrant.tech/documentation/concepts/vectors/), [payload indexing](https://qdrant.tech/documentation/concepts/indexing/), [point IDs and upserts](https://qdrant.tech/documentation/concepts/points/).
