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
- **Status**: `open`
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

- [ ] Full make check passes on the final source.
- [ ] Each complete profile starts independently and passes smoke checks.
- [ ] Task, board and implementation evidence are synchronized.

## Forbidden Actions

Do not report interrupted tests or partial service startup as complete acceptance.

## Output Requirements

Preserve partial verification evidence and keep the task blocked until resolved.
