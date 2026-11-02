---
id: impl-t-025-pr65-fixes
title: T-025 PR 65 review follow-up
type: report
domain: platform
module: queue
tags: [implementation, T-025, pr-65]
priority: 2
---
# T-025 PR 65 review follow-up

## Record Metadata

- **Owner**: `teammate-b`
- **Executor**: `codex-b`
- **Status**: `complete`
- **Date**: `2026-10-31`
- **Scope**: Non-blocking review findings at f503500; supplements T-025.md.
- **Review**: https://github.com/T1xNTH/bank-assistant/pull/65#issuecomment-6542346379
- **Commit**: `183c8dd`; mapped in task-commit-map.md.

## Changes and Findings

1. Remove both worker mounts. Only the API retains audit storage and the API-key
   registry; the worker does not need either filesystem capability.
2. Give the production worker a hostname-based name and add a Compose healthcheck
   that looks up that exact worker's Redis registration and heartbeat. Other
   replicas cannot make this worker healthy. Missing/stopped/stale registrations
   and Redis failures fail closed. Redis calls have 2s timeouts. The freshness
   window follows RQ's default worker TTL plus grace (480s), accommodating its
   blocking idle dequeue. Busy jobs retain the monitoring parent's heartbeat.
   The healthcheck process avoids importing the LLM/Presidio stack.
   Docker marks failures unhealthy; restart policy handles exited processes only.
3. Document the existing attempt-based token policy: authenticated valid enqueue
   attempts consume a token even if enqueue later returns 503. No refund or unsafe
   separate capacity pre-check is introduced. A regression checks 202 -> 503 ->
   429 with a two-token bucket and a one-job queue.

## Verification Evidence

- Focused API/unit: 46 passed in 71.63s; covers all six healthcheck cases and
  the documented 503 token policy.
- Real Redis/worker/Compose integration: 8 passed in 132.37s, including the
  production worker subprocess's healthcheck and resolved Compose mount removal.
- Full non-integration suite: 672 passed, 34 deselected in 205.78s.
- Ruff and diff whitespace checks passed.

## Completion Outcome

Task remains in review; independent re-review and counterpart approval are pending.
No contract change, self-approval or merge is claimed.
