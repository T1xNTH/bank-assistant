---
id: adr-0001-qdrant-hybrid
title: ADR 0001 — Qdrant hybrid retrieval
type: reference
domain: architecture
module: rag
tags: [adr, qdrant, hybrid, t-043]
priority: 2
---
# ADR 0001 — Qdrant hybrid retrieval

- **Date**: `2026-11-06`
- **Owner**: `trong-hung`
- **Status**: `Retrospective implemented-design record; reviewed in T-043 (claude-review-b, APPROVED)`
- **Authority**: Existing SRS/DEC-001 and merged retrieval/T-038 work; no new approval.

## Context

Vietnamese banking questions mix semantic wording with exact product names,
document identifiers and fee-table terms. The service also needs file/page
citations, department constraints and dense-only comparison during evaluation.

## Decision

Use bge-m3 dense and sparse representations in Qdrant. `dense` uses cosine search;
`hybrid` fuses filtered dense/sparse prefetches with Qdrant RRF. Each branch fetches
at least 20 candidates or requested k. Application default `hybrid_rerank` reranks
hybrid candidates through the reranker and returns up to k=5 hits above the refusal
threshold. Defaults are eight rerank candidates and threshold 0.5; configured k can
increase the fetched candidate count. No permitted/sufficient hits means refusal.

Query-time access/superseded filters apply before fusion and ranking, as detailed
in [ADR 0003](0003-payload-rbac.md). Keep dense/hybrid modes for comparison rather
than treating a single retrieval choice as a universal accuracy claim.

## Consequences and alternatives

- Dense-only is simpler but may miss exact identifiers; sparse-only loses semantic
  matching. Both remain representation inputs, with dense-only an exposed mode.
- RRF avoids calibrating raw dense/sparse score scales. The cross-encoder adds CPU
  latency; eight candidates are a documented quality/latency tradeoff, not proof
  that all relevant answers fit that cutoff.
- Collection schema, embedding dimensions and chunker must match. Snapshot restore
  preserves an index; it does not prove a changed chunker or fresh PDF print is equivalent.
- Saved T-038 default-mode hit@5 is 0.90 and answer rate 35/40. Full eval and query
  traces remain the evidence; a fake demo is not a retrieval benchmark.

## Evidence

- [Retrieval](../../../src/app/rag/retrieve.py), [store](../../../src/app/rag/store.py), [rerank](../../../src/app/rag/rerank.py).
- [Query/filter tests](../../../tests/unit/test_retrieve.py), [evaluation notes](../../12-ai/rag-eval-notes.md).
- [SRS](../../01-business/srs.md), [DEC-001](../../../.agent/governance/decisions/DEC-001.md).
