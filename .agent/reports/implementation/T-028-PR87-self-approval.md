---
id: impl-t028-pr87-self-approval
title: T-028 PR87 self-approval prohibition
type: report
domain: platform
module: agent-storage
tags: [T-028, PR87, approval, sqlite]
priority: 2
---
# T-028 PR87 self-approval follow-up

## Record Metadata

- **Task ID**: `T-028`
- **Epic ID**: `E-011`
- **Owner**: `teammate-b`
- **Executor**: `codex-b`
- **Status**: `complete`
- **Date**: `2026-11-02`
- **Implementation Commit**: `ffebd22`
- **Review and Owner Decision**: https://github.com/T1xNTH/bank-assistant/pull/87#issuecomment-6568634202
- **Prior Evidence**: `.agent/reports/implementation/T-028.md`, `T-028-PR87-fixes.md` (preserved)

## Changes

Owner A decided that the approver must differ from the ticket creator. After
validating non-empty string inputs, TicketStore.create rejects a matching approver
identity with PermissionError before any directory/database access. README and
TicketDecision document the restriction. No existing ticket is modified.

The requested self-approval parameterized test verifies no directory/database is
created. Another regression verifies self-approval leaves an existing database
unchanged. The SQL injection regression still binds attacker-controlled text in
all three fields, using distinct creator/approver identities under the new rule.
Ordinary cross-user approvals remain covered by persistence/concurrency tests.

## Verification Evidence

- Focused SQLite tests: `41 passed in 3.30s`.
- Ruff: `All checks passed!`.
- WSL `make check PY=/home/viet_anh/.venvs/bank-t011/bin/python`: `806 passed,
  50 deselected in 116.76s`; Ruff pass; `FRAMEWORK_VALIDATION_PASS`.
- `git diff --check`: passed before implementation commit.

## Outcome

Implementation ffebd22 is committed, mapped in Git Nexus and validated. This supersedes the
previous pending self-approval policy note, based on the linked owner decision.
T-028 remains in review; independent re-review and counterpart approval pending.
