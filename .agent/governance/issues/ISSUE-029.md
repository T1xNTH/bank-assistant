---
id: issue-029
title: T-032 merged but dependency lifecycle remains review
type: governance
domain: integrations
module: execution
tags: [issue, lifecycle, T-032, T-033]
priority: 2
---
# ISSUE-029: T-032 dependency closure

## Record Metadata

- **Issue ID**: `ISSUE-029`
- **Owner**: `trong-hung`
- **Reporter**: `codex-b`
- **Status**: `open`
- **Issue Type**: `inconsistency`
- **Priority**: `2`
- **Created Date**: `2026-11-03`

## Description

T-032's task file says pending and its board row says review. PR #95 was approved
by Vietanhhhhhh2003 at head b26fa4d and merged as 7f4eb73 on 2026-11-03. The user
explicitly requested T-033 implementation after that merge. The T-033 lifecycle
command still refuses to start because T-032 is not done on the board.

## Evidence

- `python scripts/agent --actor codex-b task start T-033` returns
  `agent: error: T-033: dependencies not done: T-032` without writes.
- [PR #95](https://github.com/T1xNTH/bank-assistant/pull/95): approved, merged.
- `.agent/execution/task-board.md`, `.agent/execution/tasks/T-032.md`.

## Impact

Implementation proceeds under the explicit user request, based on merged T-032
source. T-033 remains administratively pending until the owner reconciles T-032
closure and the CLI can record its lifecycle. No T-032 self-approval or fabricated
independent review record is introduced.

## Resolution

Open. Owner must reconcile T-032 task/board using existing external approval and
required review evidence, then start/report/request review for T-033 via the CLI.
This record does not replace acceptance evidence or authorize marking tasks done.

## Related Files

- **Tasks or Epics**: `T-032`, `T-033`, `E-012`
- **Report**: `.agent/reports/implementation/T-033.md`

## Acceptance Criteria

- [ ] T-032 task and board agree with its authorized completion evidence.
- [ ] T-033 lifecycle can proceed through the CLI without bypassing dependency checks.
