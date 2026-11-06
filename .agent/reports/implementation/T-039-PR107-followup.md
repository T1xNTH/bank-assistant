---
id: impl-t039-pr107-followup
title: T-039 PR 107 review follow-up
type: report
domain: devops
module: ci
tags: [implementation, t-039, ci, review-follow-up]
priority: 2
---
# T-039 PR 107 review follow-up

## Record Metadata

- **Task ID**: `T-039`
- **Owner**: `teammate-b`
- **Executor**: `codex-b`
- **Status**: `complete`
- **Report Date**: `2026-11-06`

## Scope and Changes

This report supersedes the current-state descriptions in [T-039.md](T-039.md) and
[T-039-handoff.md](T-039-handoff.md). Their historical evidence is preserved.
Scope: remaining comments on [PR #107](https://github.com/T1xNTH/bank-assistant/pull/107),
including A's [completed F-01 handoff](https://github.com/T1xNTH/bank-assistant/pull/107#issuecomment-6662112852).

- **F-01/F-03**: A's `1c84474` adds path selection and the median of three faithfulness
  judgments per answer. Docs/UI/record-only PRs skip the paid eval; main pushes and manual
  runs always evaluate. `check` accepts skipped eval only after successful `eval-changes`
  with `eval=false`. Failed/cancelled checks still block. Judge, prompt, golden subset and
  thresholds stay unchanged. Correct the CI job table to describe the skip exception.
- **F-05**: remove `RERANK_CANDIDATES` and `REFUSAL_THRESHOLD` from the workflow environment.
  The evaluator uses the code defaults and records the effective configuration in its report.
  Current defaults remain 8 and 0.5; future code changes reach CI without editing a second copy.
- **F-02/F-04**: retain the negative-control evidence and restored production prompt;
  refresh the PR evidence with A's median/path-filter changes and this follow-up.

## Verification Evidence

- Independently fetched [CI 42054748005](https://github.com/T1xNTH/bank-assistant/actions/runs/42054748005)
  at `1c84474`: all six jobs succeeded. Live eval log reports faithfulness **1.0**,
  coverage **1.0** (8/8), hit@5/refusal/citation/answer rate **1.0**, zero errors/retries.
  This validates A's changes before the F-05 cleanup, not the final follow-up commit.
- [Negative control 42003025297](https://github.com/T1xNTH/bank-assistant/actions/runs/42003025297):
  real eval/check failed (faithfulness 0.0, 1/8 answered); `fad669b` reverted `cdc5dad`.
  [Post-revert 42005802558](https://github.com/T1xNTH/bank-assistant/actions/runs/42005802558)
  was green. The later median implementation intentionally changes `eval/run.py`;
  the original report's empty-diff claim for that file applies only to the restoration step.
- `actionlint v1.7.12 .github/workflows/ci.yml`, framework validator and `git diff --check`: passed.
- Executed the workflow's path-selection shell with controlled changed-file inputs: **20 PR
  path cases**, push/manual events, and git failure passed. Docs/UI/records/tests skip;
  RAG/eval/dependencies/workflow paths run. This is local shell validation, not a hosted skip run.
- Executed the aggregate-check shell for **2048 combinations** of upstream job results,
  `eval=true/false` and eval results: all passed. Only successful prerequisites plus the
  required successful/skipped eval combination pass.
- Windows system Python could not run pytest (not installed). Its older Ruff reported seven
  pre-existing UP038 findings; no source rewrite was made to satisfy that unrelated tool version.
  Verification uses the Linux environment with repository requirements instead; Linux Ruff passed.
- `git diff` against freshly fetched main is empty for `src/app/prompts.py`,
  `tests/unit/test_answer.py` and `eval/thresholds.json`.
- Linux focused pytest (`tests/unit/test_ci_golden.py tests/unit/test_eval_run.py -q`):
  **65 passed**, one dependency deprecation warning, 16.92 seconds. Linux Ruff passed.
- A separate Linux full-suite run was still in progress when this report was finalized;
  it is not claimed as a pass. Final-head hosted quality/backend/eval results will be
  linked in the PR evidence after push, without rewriting this completed report.

## Limits and Handoff

- A's run exercised `eval=true`. A docs/UI-only hosted PR has not yet demonstrated the
  `eval=false` skip branch; do not claim hosted evidence for it.
- Three judgments reduce noise without guaranteeing deterministic scoring. Public smoke
  questions do not replace full-corpus, RBAC/confidential, local-model or NFR-08 QA.
- Task remains `review`. This implementation report does not provide independent Claude
  review, counterpart approval, or permission to merge.
