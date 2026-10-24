---
id: test-strategy
title: Test Strategy
type: reference
domain: testing
module: tests
tags: [testing, pytest, eval]
priority: 2
---
# Test Strategy

| Layer | Tool | Where | Runs in |
|---|---|---|---|
| Unit | pytest | `tests/unit/` | CI on every PR |
| API | pytest + FastAPI TestClient, fake backends | `tests/api/` | CI on every PR |
| Security | pytest (RBAC leakage, PII scan, injection, HITL) | `tests/security/` | CI on every PR |
| Framework | `scripts/validate-framework.py`, `tests/framework/` | | CI on every PR |
| Integration | pytest marker `integration` (needs compose) | `tests/integration/` | locally / release QA |
| Quality | RAGAS + custom metrics on `eval/golden.jsonl` | `eval/` | CI `eval` job (subset) + release QA (full) |

Rules: TDD for logic; fakes from `tests/fakes.py` instead of mocks of internals; test output must be clean; NFR thresholds live in `eval/thresholds.json`.
