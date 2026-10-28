---
id: impl-t004-ci-runtime
title: T-004 CI runtime follow-up
type: report
domain: platform
module: ci
tags: [implementation, t-004, ci, docker, smoke]
priority: 2
---
# T-004 CI runtime follow-up

## Record Metadata

- **Owner**: `teammate-b`
- **Executor**: `codex`
- **Status**: `complete`
- **Task ID**: `T-004` (platform validation follow-up)
- **Epic ID**: `E-002` (includes core Compose stack and CI check)
- **Report Date**: `2026-10-28`
- **Authorization**: user requested adding backend/frontend CI checks after discussion of missing build/start/E2E coverage. This adds platform regression validation in the active E-002; it does not expand E-016 or alter a runtime/API contract. UI was found to be a scaffold and that limitation was reported before implementation.

## Scope

- Build and start the existing API Docker image, Redis and Qdrant in CI; exercise the running API over HTTP.
- Retain the required check name `check`, now as a gate requiring quality, backend-smoke and ui-syntax success.
- Add an isolated CI Compose overlay, a standard-library HTTP smoke script and documentation.
- UI syntax checks only: no implemented frontend exists in main. No Streamlit dependency or blank frontend runtime is introduced to imply coverage that does not exist.
- No real LLM/RAG calls, cloud secrets, OCR/model downloads, PDF corpus recreation or new frontend functionality.

## Changes Made

| Artifact | Change |
|---|---|
| `.github/workflows/ci.yml` | quality, backend-smoke, ui-syntax, aggregate check; read-only repository permission; manual trigger; cancellation of older runs; runtime timeout, service logs and cleanup |
| `infrastructure/compose.ci.yaml` | merge with the real Compose file; discard local env-file loading and host ports; force fake backends and service DNS URLs |
| `scripts/smoke_api.py` | live HTTP checks for health, answer/citations/mode, refusal, validation, 404, request IDs; optional Qdrant readiness; failures return nonzero |
| `docs/07-development/ci.md`, `index.md` | coverage, limitations and exact local reproduction/cleanup commands |
| task record, board, sessions | link the user-authorized supplemental CI work; retain task review status and prior evidence |

## Verification Evidence

Isolated worktree based on main `3d83f4f`; original workspace modifications preserved.

- Linux/WSL `make check PY=/mnt/d/bank-assistant/.venv/worktrees/t003/.venv/bin/python`: Ruff passed, **57 passed in 56.01s**, `FRAMEWORK_VALIDATION_PASS`.
- Official actionlint v1.7.12 against the updated workflow: passed.
- UI and smoke script compilation: passed.
- Compose resolved configuration: no local env file, no published host ports, exactly fake backend selectors and internal Qdrant/Redis URLs; separate project `bank-assistant-ci-local` and its own volume.
- Actual Docker build and `up -d --build --wait --wait-timeout 180`: passed; API/Redis healthy and Qdrant running.
- Streamed smoke script into the API container, same command as workflow: **API smoke passed** (health, answer/citations, refusal, validation, 404, request IDs); **Qdrant readiness passed**.
- `docker compose exec -T redis redis-cli -e ping`: **PONG**.
- Negative test with base URL `http://127.0.0.1:1`: smoke failed with connection refused and exit **1**, as intended.
- Container status confirmed no host port mappings. Cleanup `down --volumes --remove-orphans` removed only the isolated CI project's containers, network and temporary volume.
- `git diff --check`: passed.
- GitHub-hosted execution is pending branch publication/PR at the time this report was written; no claim of a remote pass is made here.

## Review and Limitations

- Existing independent T-004 approvals apply to earlier changes only. This supplemental work requires its own review; no self-approval, task done transition, merge or branch-protection edit was performed.
- Fake answer/auth/LLM paths test packaging and HTTP behavior, not real retrieval or service usage inside the answer pipeline. Redis and Qdrant are probed independently.
- UI still has no runtime/build or browser E2E coverage. Replace the explicit ui-syntax job when E-016 delivers the app.
- Older native Windows framework failures remain tracked separately; this follow-up validates the Linux CI environment, not Windows portability.
- Prior final reports remain unchanged. This report supplements them and is not an independent review or QA approval.
