---
id: implementation-t040-verification-retry
title: T-040 conflict resolution and Linux verification retry
type: report
domain: devops
module: infrastructure
tags: [T-040, verification, compose, recovery]
priority: 2
---
# T-040 verification retry

- **Owner**: `teammate-b`
- **Author**: `codex`
- **Status**: `complete`
- **Date**: `2026-11-04`
- **Scope**: User requested rerunning failed checks and resolving PR #104 conflicts.
- **Source**: Merge `c68dc28` of main `b711377`; verification workflow/helper `ec61df4`, trigger `b312b71`.
- **Prior Report**: `.agent/reports/implementation/T-040.md`.

## Changes and Conflict Resolution

The only merge conflict was adjacent T-035/T-036 board entries. Preserve main's
T-035 done entry and T-036 review state/evidence; retain T-040's blocked state.
Both session and commit-map histories are preserved. Main's token-cost/feedback
implementation and task records are included. PR #104 reports MERGEABLE.

Add the Compose and Qdrant recovery workflow and a reusable Make recovery smoke
script. The workflow runs exact make check on Linux, then starts core services
plus each optional profile from stopped containers and exercises actual Make
backup/restore using seven uniquely named synthetic points. Its cleanup affects
only the ephemeral CI project and generated collection. No contract changes.

## Verification

- [Linux make-check job](https://github.com/T1xNTH/bank-assistant/actions/runs/41774000720/job/126389989328)
  at b312b71: **1228 passed, 80 deselected**, one upstream LangChain warning,
  Ruff clean and FRAMEWORK_VALIDATION_PASS. Exact command: `make check PY=python`.
- [Standard CI](https://github.com/T1xNTH/bank-assistant/actions/runs/41774000654):
  all four jobs passed: quality, UI syntax, backend smoke and aggregate check.
- [Independent profiles and recovery](https://github.com/T1xNTH/bank-assistant/actions/runs/41774000720/job/126389989160):
  passed. Each of local-llm, automation and obs started with all core services,
  passed Docker health and Make smoke checks, and restored seven points with
  identical vectors/payloads using actual Make targets. Containers were stopped
  between profiles; each emitted PROFILE_PASS and MAKE_RECOVERY_PASS.
- Local WSL still fails startup with error 6 / Wsl/Service/CreateInstance/E_FAIL;
  verification uses fresh GitHub Linux runners instead. Local files/volumes are preserved.

## Independent Review

Fresh Claude session `2bc91da5-aee3-4a33-ac5f-874ed51d99a5` failed OAuth before
source execution (zero model tokens and API duration). Shared workspace evidence:
`output/t040-review-retry.json`. BLOCKER-008 remains open. No review result,
counterpart approval, T-040 done or merge is claimed.

## Outcome

Full Linux make check and complete profile/recovery acceptance are verified.
BLOCKER-009 is resolved using a separate Linux runner; local WSL repair is not
claimed. Implementation reports are complete. T-040 remains blocked on
BLOCKER-008; no independent approval, task done or merge is claimed.
