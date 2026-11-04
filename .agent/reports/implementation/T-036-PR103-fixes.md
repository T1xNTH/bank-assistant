---
id: impl-t036-pr103-fixes
title: T-036 PR 103 review fixes
type: report
domain: platform
module: tracing
tags: [implementation, T-036, review, cost]
priority: 2
---
# T-036 PR 103 review fixes

- **Owner**: `teammate-b`
- **Author**: `codex`
- **Date**: `2026-11-04`
- **Status**: `complete`
- **Scope**: PR #103 review F-01, F-02, O-01 and O-02.
- **Source commit**: `e7220a9`.
- **Prior evidence**: [T-036 implementation](T-036.md),
  [handoff](T-036-handoff.md), and
  [independent review](https://github.com/T1xNTH/bank-assistant/pull/103#pullrequestreview-5756670873).

## Findings and changes

- **F-01**: Resolve the actual model from `x-litellm-model-name`, falling back to
  the response body's model when the header is missing or empty. A response with
  body model `cloud-chat`, header `openai/gpt-6-luna`, and 8 input/4 output tokens
  now produces the table estimate `2.8e-6` USD in accounting and generation cost.
- **F-02**: Look up the raw model before masking and retain only numeric
  `meta.cost_usd`; no raw model name is added to metadata. Generation accounting
  consumes this value, including explicit unknown/zero prices, while custom
  clients/fakes without the metadata retain the existing table lookup. Snapshot
  `gpt-4.1-mini-2025-04-14` is priced correctly while its exported name stays masked.
- **O-01/O-02**: Document audit failure behavior for HTTP/worker jobs and the lack
  of trace ownership checks on feedback. No ownership/contract behavior changed.

## Verification

- Linux Python 3.12 focused check: `pytest tests/unit/test_llm.py
  tests/unit/test_llm_cost.py tests/unit/test_tracing.py tests/api/test_request_cost.py
  tests/api/test_feedback.py -q`: **101 passed**. Includes real HTTP stub gateway,
  SQLite audit, real Langfuse 4.18.0 with in-memory OTEL export, missing/empty
  headers, masked snapshot/PII names, unknown/free models and missing usage.
- Ruff and framework validator passed; `git diff --check` passed.
- Full `make check PY=/home/viet_anh/.venvs/bank-t011/bin/python` in WSL:
  Ruff clean, **1154 passed, 20 skipped, 79 deselected**,
  `FRAMEWORK_VALIDATION_PASS`.

## Environment and completion limits

An initial Python 3.13 Windows attempt crashed in logging during collection.
Python 3.11 Windows focused tests passed (100 passed, 1 skipped). The fresh Linux environment passed the
final 101 focused cases but full collection lacked Docling/Torch. Full validation
was moved to the existing WSL environment with these dependencies; the partial
suite run was interrupted in favor of the complete check. That partial run had
one framework lifecycle failure while the report was being prepared; rerunning
that case in the final WSL environment passed, as did the complete suite.

No live gateway/provider request or Langfuse server ingestion is claimed. The
independent reviewer can repeat the live gateway check from their review.
Task remains `review`; this follow-up does not self-approve or merge the PR.
