---
id: adr-0003-payload-rbac
title: ADR 0003 — Query-time payload RBAC
type: reference
domain: architecture
module: security
tags: [adr, rbac, qdrant, t-043]
priority: 2
---
# ADR 0003 — Query-time payload RBAC

- **Date**: `2026-11-06`
- **Owner**: `trong-hung`
- **Status**: `Retrospective implemented-design record; reviewed in T-043 (claude-review-b, APPROVED)`
- **Authority**: Existing SRS department isolation and superseded-document requirements.

## Context

Relevant chunks can belong to another department or a superseded document.
Filtering only after top-k can return too few allowed hits and risks exposing
forbidden context to later stages. UI labels and model-supplied arguments are untrusted.

## Decision

Resolve `User` from a SHA-256 API-key registry. Retrieval accepts a trusted user,
rejects unknown departments and applies both payload conditions:

```text
department IN {"public", authenticated_user.department}
AND superseded_by IS NULL
```

Dense search and both hybrid prefetch branches apply the filter inside Qdrant,
before fusion, reranking and prompt construction. The ingested representation
uses null for current documents. Classification is a separate routing signal;
it does not grant access. Effective-date scheduling is not part of this predicate:
maintainers must update superseded labels/indexes when a replacement becomes current.

Transaction tools bind their user in trusted code and query read-only SQLite by
that user's ownership. Approver/service roles do not bypass transaction ownership.
Ticket approval uses a different authenticated approver and trusted thread owner;
the UI role selector is merely a key mapping for a local demo.

## Consequences and alternatives

- Post-filtering is rejected: hidden high-ranking chunks could crowd out allowed
  results, and later code would have to avoid every accidental exposure.
- A collection per department is unnecessary for the small shared/public corpus,
  but payload correctness becomes a security invariant. Reingest changed labels
  and validate the manifest/index relationship.
- Synthetic labels exercise HR/credit/confidential behavior on public documents;
  they are not evidence that the original documents are genuinely confidential.
- Roles alone grant neither document-department access nor another user's bank rows.

## Evidence

- [Authentication](../../../src/app/security/auth.py), [registry validation](../../../src/app/security/keys.py), [access filter](../../../src/app/rag/retrieve.py).
- [Filter-before-top-k tests](../../../tests/unit/test_retrieve.py), [corpus RBAC tests](../../../tests/integration/test_rbac_leak.py).
- [Core banking](../../../src/app/agent/core_banking.py), [owner/approval API tests](../../../tests/api/test_agent.py), [corpus labels](../../07-development/corpus.md).
