---
id: impl-t-025-pr65-restart
title: T-025 PR 65 worker restart correction
type: report
domain: platform
module: queue
tags: [implementation, T-025, pr-65, worker]
priority: 2
---
# T-025 PR 65 worker restart correction

## Record Metadata

- **Owner**: `teammate-b`
- **Executor**: `codex-b`
- **Status**: `complete`
- **Date**: `2026-10-31`
- **Scope**: Restart finding at 567736b; supersedes the worker identity approach
  in T-025-pr65-fixes.md, preserving its historical verification evidence.
- **Review**: https://github.com/T1xNTH/bank-assistant/pull/65#issuecomment-6542840330

## Changes and Findings

- Use RQ's default random worker name on every startup. An unexpired registration
  from a killed worker cannot collide with the replacement's registration.
- Healthcheck discovers registrations through Worker.all and checks the local
  hostname, live PID, state and heartbeat. Other hosts and dead processes cannot
  satisfy health. Existing Redis timeouts and heartbeat tolerance remain.
- No old registration is deleted; RQ retains responsibility for its expiration.
- Regression exercises the production constructor and RQ register_birth with an
  undeclared prior death; only the replacement can satisfy health in that test.
- Real Redis production-entrypoint integration starts with the old hostname-based
  registration still present, completes an API job and passes healthcheck while
  preserving the old key.
- Healthcheck remains observational; Docker's restart policy does not restart
  unhealthy containers, as already documented in README.

## Verification Evidence

- Focused queue policy tests: 18 passed.
- Real Redis/worker/Compose integration: 8 passed in 41.89s.
- Ruff and diff whitespace checks passed.
- Full make check: 674 passed, 34 deselected in 136.15s; Ruff passed and
  FRAMEWORK_VALIDATION_PASS.

## Completion Outcome

Task remains in review pending independent re-review and counterpart approval.
No approval, merge or task completion is claimed.
