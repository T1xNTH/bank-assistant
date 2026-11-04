---
id: impl-t040-pr104-review-fixes
title: T-040 PR104 Review Corrections
type: report
domain: devops
module: infrastructure
tags: [T-040, implementation, review-follow-up]
priority: 2
---
# T-040 PR104 Review Corrections

- **Owner**: `teammate-b`
- **Author**: `codex`
- **Status**: `complete`
- **Date**: `2026-11-04`
- **Source**: `9828d5b`, following A's review of `d83d96c`.
- **Prior Reports**: `T-040.md`, `T-040-verification-retry.md` remain historical evidence.

## Changes

Respond to [A's review](https://github.com/T1xNTH/bank-assistant/pull/104#issuecomment-6625024071).
Remove the two blank lines detaching T-040 mappings from the Markdown table.
Catch HTTPError only around remote snapshot deletion and print a fixed stderr
warning. A completed backup stays successful and an earlier collection-change
error remains the reported failure; partial-file cleanup remains unchanged.
Align workflow installation with `httpx2>=2.14` as in requirements.txt.

## Verification

Four new cases cover HTTP 500/connection failure after successful backup and
after collection change. All four fail before correction and pass afterward;
all **15** backup/restore/profile unit cases pass after the change. Success checks
manifest, bytes, digest and count; failure retains the previous manifest and
original exception. Warning excludes raw connection details and no partial files
remain. Native run uses `--confcutdir=tests/unit` because these standalone script
tests need no application-wide autouse Redis fixture.
Ruff, framework validation and git diff check pass. Fresh Linux full-suite and
profile/recovery verification will be recorded in the task QA report.

## Review Disposition

Record A's actual independent review, conditional approve instruction and
task-specific OAuth substitution in review/T-040.md and BLOCKER-008. Lifecycle
commands resume task, request/start review and record A's approval. The original
complete implementation report is preserved byte-for-byte after the CLI request.
No fresh Claude execution, repaired OAuth, new external re-review, GitHub PR
approval, task completion or merge is claimed. Task remains review for QA and
counterpart approval.
