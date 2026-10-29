---
id: impl-t014-review-fixes
title: T-014 independent review corrections
type: report
domain: security
module: src/app/security
tags: [implementation, t-014, review-fixes]
priority: 2
---
# T-014 review corrections

## Record Metadata

- **Owner**: `teammate-b`
- **Executor**: `codex`
- **Status**: `complete`
- **Task ID**: `T-014`
- **Report Date**: `2026-10-29`
- **Implementation Commit**: `7f0fa00`
- **Scope**: Corrections for T014-F01 and T014-F02, recorded by independent reviewer `codex-review-t014` in [first-round review](../review/T-014.md) and ISSUE-018.

## Changes Made

- Compose mounts the host config directory read-only at `/app/config`. Directory mounting keeps atomic registry replacement visible inside the running container.
- Sample registry is now a valid empty digest map. Provisioning and authentication share the same registry validation in `app.security.keys`; malformed existing registries fail before modification or secret output.
- Added sample-to-provision-to-authenticate and incompatible-registry regression cases; auth suite increased from 22 to 25 tests.
- Updated the auth guide with container path/mount and revocation instructions.

## Verification Evidence

- Native Windows `pytest tests/security/test_auth.py -q`: **25 passed in 1.97s**. Focused Ruff passed.
- Real Docker Compose smoke: validated effective read-only `/app/config` mount; valid key returned 200, missing key 401, and replacing the host registry atomically revoked the key (401) without container restart.
- Smoke used the existing `bank-assistant-api:t004` image with the current `src/` mounted read-only; this exercises the deployed Compose directory mount and current application. It does not claim a fresh dependency/image build. Only an isolated one-off API container/network was started; no external LLM or data services were called. Temporary synthetic registry and container were removed.
- Initial smoke wrapper failed because installed Compose does not accept `run --no-build`; removing that unsupported flag allowed successful execution. No failed run is claimed as pass.
- Independent reviewer will rerun full `make check` and the deployed smoke after these corrections; no approval is claimed here.

## Related Files

- Original [implementation](T-014.md) and [first-round review](../review/T-014.md) remain historical evidence. This supplement supersedes the original implementation's deployment/provisioning claims affected by F01/F02.
- Task/board status is `review`; follow-up requested through CLI for `codex-review-t014`.
- Shared current-context remains reserved for coordinator A.

## Completion Outcome

Implementation corrections are ready for independent follow-up review. T-014 is not done; human peer approval and merge remain pending. ISSUE-018 closure depends on reviewer verification.
