---
id: qa-t042-pr97-round2
title: T-042 PR 97 follow-up verification
type: report
domain: testing
module: ui/app.py
tags: [qa, T-042, pr97]
priority: 2
---
# T-042 PR 97 follow-up verification

## Record Metadata

- **Owner**: `trong-hung`
- **Tester**: `codex`
- **Status**: `passed`
- **Task ID**: `T-042`
- **Test Date**: `2026-11-03`
- **Head**: `b670cbf7c15ecce325c55d85bdea07c39d4a5a8d`

## Scope and Acceptance

Task-level UI verification: roles from environment, ask answer/citations/route, force_local, agent pending action, approve/reject, external-thread result persistence, duplicate and unknown-thread errors. Owner explicitly accepts FR-12 flow and AppTest as T-042 verification; full future demo-script execution belongs to T-043.

## Environment

WSL Python 3.12, bank-t011 environment with isolated dependency overlays, Streamlit 1.60.0. Source imports pinned to reviewed worktree. Initial UI attempt skipped because a previous temporary dependency directory was gone; rerun uses persistent workspace dependencies. Skipped execution is not counted as passed.

## Evidence

- Repository Ruff, compileall and framework validation pass.
- CI: quality, backend-smoke, ui-syntax and check pass at reviewed head.
- Focused UI: 13 passed in 114.41s, including external-thread result/ticket ID persistence, rejection, duplicate 409 and unknown 404.
- Broad local suite: 1092 passed, 1 failed, 20 skipped, 79 deselected in 257.08s. UI was skipped in that initial run because the previous temporary dependency directory was absent; all 13 UI tests were subsequently run with persistent dependencies. Other skips concern Node-dependent n8n expression checks.
- Tracing fork-test isolated rerun: failed at the same 15s subprocess limit. A diagnostic with no startup timeout measured import at 23.696s and the fork check exited 0. Original failures are preserved, not relabeled as test passes.
- Review approval CLI completed before this final task-level QA assessment. No QA CLI run: it only supports epic-level QA.

## Limits

No independent live cloud/Ollama, real RAG or browser-layout run. QA CLI implements epic-level QA only, requiring all E-016 children terminal; T-043 remains pending. No epic QA pass or task completion is claimed by this task-level verification.

## Recommendation

Conditional-go for T-042: the accepted UI scope passes and previous defects are resolved; broad repository CI is green. Local full-suite timeout and missing Node coverage are environment limitations. This is task-level verification, not an epic/release QA certification or live provider/browser run.
