---
id: impl-t-037-pr102-followup
title: T-037 PR 102 Review Follow-up
type: report
domain: platform
module: api
tags: [implementation, T-037, review-follow-up]
priority: 2
---
# T-037 PR 102 Review Follow-up

## Record Metadata

- **Task ID**: `T-037`
- **Owner**: `teammate-b`
- **Executor**: `codex`
- **Status**: `complete`
- **Report Date**: `2026-11-04`

## Scope and Changes

Respond to [A's review of a198bfd](https://github.com/T1xNTH/bank-assistant/pull/102#issuecomment-6610970158).
The original complete `.agent/reports/implementation/T-037.md` remains historical evidence.

- README now documents Redis dependency and fail-closed 503 for /ask, /chat and
  /ask/jobs, the shared budget, invalid-body charging, and fake-auth dev's shared
  burst of 10 with demo guidance.
- Record agent-endpoint rate limiting as F-01 in `.agent/reports/review/T-037.md`,
  using the explicit follow-up option offered by A. Owner teammate-b; both agent
  routes, shared budget, no side effects on 429 and outage/auth checks are specified.
- Archive A's existing review and OAuth substitution authorization in the requested
  review report. A found no merge blocker but requested recheck before approval;
  report remains changes-required, task review. No executor approval is issued.
- No runtime implementation, contracts or task acceptance criteria changed.

## Verification Evidence

- WSL `make check PY=/home/viet_anh/.venvs/bank-t011/bin/python`: Ruff passed;
  pytest **1108 passed, 20 skipped, 79 deselected, 1 failed** in 439.85s.
  Failure: `test_forked_worker_does_not_inherit_a_locked_backend` timed out waiting
  15 seconds for its Python subprocess. No tracing code or test changed in this
  follow-up. Full output: shared workspace `output/t037-pr102-check.log`.
- Native `python scripts/validate-framework.py` and `git diff --check`: passed.
- Focused recheck: **80 API/rate-limit/chat/audit tests passed**, while the same
  tracing test again hit its subprocess timeout (47.29s overall). Log:
  `output/t037-pr102-recheck.log`.
- Copying unchanged src/tests to Linux `/tmp` and rerunning only the tracing
  test also timed out (27.32s overall). The filesystem probe did not resolve it;
  no root cause is asserted. Log: `output/t037-pr102-linux-fork.log`.
- This documentation-only follow-up does not fix the pre-existing tracing test.
  Full local verification is therefore not green; CI and A's recheck remain required.

## Completion Outcome

Requested review notes are documented and the external review is archived.
Verification results, including the tracing failure, are recorded above. Await
A's recheck and counterpart PR approval. No task done, merge or issue closure is claimed.
