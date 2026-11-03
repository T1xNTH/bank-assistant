---
id: implementation-t035-review-followup
title: T-035 peer review fixes and requested technical recheck
type: report
domain: observability
module: tracing
tags: [implementation, T-035, review, qa]
priority: 2
---
# T-035 review follow-up

- **Owner**: `teammate-b`
- **Author**: `codex (executor)`
- **Status**: `complete`
- **Date**: `2026-11-03`
- **Source Commit**: `eb00db1`
- **Scope**: All three minor comments in [A peer review](https://github.com/T1xNTH/bank-assistant/pull/99#pullrequestreview-5749622651) of 7ae9279, plus the user's request to re-review and rerun QA checks.

## Findings and Resolution

| Finding | Severity | Evidence and action | Owner |
|---|---|---|---|
| A-01 flush overhead | minor | A measured approximately 1–2s additional job completion latency when Langfuse is unreachable. Documented the overhead, scope of the 2s SDK timeout and its exclusion from root/processing span duration; retained final flushing for short-lived RQ work horses. | teammate-b |
| A-02 leaked span on setup failure | minor | Initial set_attribute exceptions reset active to no-op, so cleanup lost the span. Hold span independently and always end it in finally. New real-OTEL tests inject failures in both initial attribute writes and assert end/export, context restoration and absence of raw exception data. | teammate-b |
| A-03 concurrent cold initialization | minor | lru_cache permits simultaneous misses. Serialize backend construction/cache access with a lock; reset the lock in forked children so RQ cannot inherit a permanently held lock. A four-thread cold-start test verifies one provider/client and flush target; isolated fork test verifies a child can initialize while the parent's lock is held. | teammate-b |

The executor's scoped reinspection found no additional blocking code defect in the
request, queue, masking, SDK export and obs Compose paths. This is implementation
follow-up, not independent approval. Contracts/OpenAPI, routing and persistent
job ownership remain unchanged. Existing finalized T-035.md and T-035-handoff.md
are preserved as historical evidence.

## Verification

- Focused: 22 passed in 27.11s (18 tracing cases, four rendered Compose config cases);
  Ruff clean. Initial new fork test exposed a test harness PYTHONPATH omission,
  corrected before the passing rerun. The child also has an alarm to bound a deadlock.
- Live local smoke: one passed in 31.77s. Twenty ask requests, one chat and two job
  calls produced 23 readable traces with masked synthetic input and correct IDs,
  retrieve/rerank/llm hierarchy and queue_wait/processing split. Models, embeddings
  and reranker are scripted; Qdrant in-memory and fakeredis. This is not production QA/load certification.
- Final full regression: 1091 passed, 79 deselected in 235.90s; Ruff clean; FRAMEWORK_VALIDATION_PASS; git diff --check clean. One upstream LangChain pending-deprecation warning.
- Baseline CI at 7ae9279: all four jobs passed (quality, backend-smoke, ui-syntax, check).
  These baseline jobs do not certify the new source head.

## Review and QA Gate

Fresh separate Claude session 85fc26de-9bf9-408c-9cf1-2383bc28a0db again failed
OAuth before any source/model execution, with zero API duration and zero model
tokens. BLOCKER-007 remains open. A's review is COMMENTED and explicitly does not
replace DEC-004 review. No reviewer lifecycle start/approve or formal QA pass
was issued by the executor. The user's requested technical checks are recorded in
qa/T-035-recheck.md with the formal gate blocked. Task remains review and PR draft.

## Evidence

Shared workspace output/t035-r2-focused.log, t035-r2-full.log, t035-r2-live.log,
and t035-r2-review-attempt.json. Authentication credentials are excluded from reports.

## Outcome

Three peer comments addressed and technical checks pass at eb00db1. Await
independent reviewer authentication/approval, subsequent formal QA and counterpart
PR approval. No task done, merge or release is claimed.
