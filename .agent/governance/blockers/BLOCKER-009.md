---
id: blocker-009
title: T-040 full verification interrupted by host storage and WSL failure
type: governance
domain: devops
module: infrastructure
tags: [blocker, T-040, verification, environment]
priority: 2
---
# BLOCKER-009

## Record Metadata

- **Blocker ID**: `BLOCKER-009`
- **Owner**: `teammate-b`
- **Reporter**: `codex`
- **Status**: `resolved`
- **Blocker Type**: `environment`
- **Created Date**: `2026-11-04`

## Blocking Condition

The isolated t040 Docker runtime build installed requirements successfully but
failed during image export/unpack with a fatal error. Docker CLI then returned
SIGBUS. Windows Get-Volume measured C: SizeRemaining=0; D: still had 157 GB free.
After VM failure C: recovered about 7.3 GB, but Ubuntu-24.04 startup failed with
Wsl/Service/CreateInstance/E_FAIL, error 6, failure step 2. A targeted distro
termination reported success; the following startup remained unresponsive.
No user files, volumes or unrelated images were deleted.

## Impact

Full runtime startup for each profile and Linux make check cannot be certified.
The Linux suite was passing through 30% before the host/CLI crash interrupted it;
this is not a passing full-suite result. The initial Windows environment also
lacked Docling/Torch and cannot replace Linux validation.

Before the failure, Qdrant, automation services and all seven obs services were
healthy; two real disposable collection recovery drills passed with full vector
and payload equality. Core API/worker plus each isolated profile remain unverified.

## Related Files

- `.agent/execution/tasks/T-040.md`
- `.agent/reports/implementation/T-040.md`
- Shared workspace `output/t040-linux-check.log`, `output/t040-full.log`.
- Shared workspace `output/t040-profiles.sh`, `output/t040-make-drill.py`.

## Resolution Plan

Restore sufficient host storage and a working Ubuntu/Docker environment, or use a
separate Linux runner. Run make check with requirements-dev installed. Run each
documented make up PROFILE command from stopped t040 services, verify health and
smoke endpoints, then make down without deleting volumes. Rerun the disposable
snapshot integration drill. Obtain independent review after BLOCKER-008 clears.

## Completion Criteria

- [x] Full make check passes on the final source.
- [x] Each complete profile starts independently and passes smoke checks.
- [x] Task, board and implementation evidence are synchronized.

## Forbidden Actions

Do not report interrupted tests or partial service startup as complete acceptance.

## Output Requirements

Preserve partial verification evidence and keep the task blocked until resolved.

## Verification Retry 2026-11-04

Local WSL still fails startup, so use the permitted separate Linux runner.
Exact `make check PY=python` passed at b312b71: 1228 passed, 80 deselected,
Ruff clean and FRAMEWORK_VALIDATION_PASS. Evidence:
https://github.com/T1xNTH/bank-assistant/actions/runs/41774000720/job/126389989328.
Independent complete profile startup/recovery remains in progress; keep this
record open until its runtime criteria also pass.

## Resolution 2026-11-04

Resolved through the separate Linux runner allowed by the resolution plan:
[run 41774000720](https://github.com/T1xNTH/bank-assistant/actions/runs/41774000720)
passed exact make check and all three complete profiles at b312b71. Each profile
starts core API/worker/LiteLLM/Qdrant/Redis plus its optional services, passes
health and Make smoke checks, and passes a seven-point Make backup/delete/restore
drill comparing vectors and payloads. Containers are stopped between profiles.
[Standard CI 41774000654](https://github.com/T1xNTH/bank-assistant/actions/runs/41774000654)
also passed all four jobs including backend smoke. Local WSL is not repaired;
this resolves the verification dependency using fresh Linux runners. T-040
remains blocked only on the independent review gate, BLOCKER-008.
