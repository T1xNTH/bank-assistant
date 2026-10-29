---
id: issue-018
title: T-014 deployed API cannot read API key registry
type: governance
domain: security
module: auth
tags: [issue, t-014, auth, deployment]
priority: 2
---
# ISSUE-018: T-014 auth deployment and provisioning integration

## Usage Purpose

Track independent T-014 review findings T014-F01 and T014-F02.

## Record Metadata

- **Issue ID**: `ISSUE-018`
- **Title**: `Deployed API registry unavailable and sample provisioning incompatible`
- **Owner**: `teammate-b`
- **Reporter**: `codex-review-t014`
- **Status**: `open`
- **Issue Type**: `defect`
- **Priority**: `2`
- **Created Date**: `2026-10-29`
- **Target Date**: `none`

## Description

T014-F01: Compose API has no volume providing the registry. Dockerfile copies
only requirements and src; .dockerignore excludes config/api_keys.json.
The new host provisioning guide cannot supply keys to the deployed API.

T014-F02: The tracked example uses an envelope while the loader expects a flat
digest map. Provisioning into a copy succeeds but produces an unusable registry.

## Impact

- **Affected Scope**: `T-014 auth deployment and provisioning`
- **Severity**: `high`
- **User or Delivery Impact**: Enabling apikey authentication in the supported Compose stack returns 503 for valid provisioned keys.

## Reproduction Evidence

- **Preconditions**: Host provisioning per auth guide; Compose deployment with AUTH_BACKEND=apikey.
- **Steps**: Inspect image COPY paths and Compose API volumes. For sample issue, copy config/api_keys.example.json to a temporary path, run make_key.py against it, then load_api_keys.
- **Observed Result**: No deployed registry path can be populated by host provisioning. Sample reproduction independently returned generator exit 0 and key emitted, followed by loader ValueError. Actual Docker auth execution was not run in this review.
- **Expected Result**: Valid generated key resolves its User in deployed API; missing/invalid keys return 401; revocation is visible without recreating the container.
- **Evidence Paths**: `.agent/reports/review/T-014.md`

## Related Files

- **Affected Files**: `infrastructure/compose.yaml`, `docs/07-development/auth.md`, `config/api_keys.example.json`, `scripts/make_key.py`
- **Tasks or Epics**: `T-014`, `E-006`
- **Decisions**: `DEC-001`, `DEC-004`
- **Risks**: `none`
- **Blockers**: `none`

## Acceptance Criteria

- [x] Root causes and proposed corrections are recorded in independent review.
- [ ] Provide the registry through a read-only directory mount without baking keys into the image.
- [ ] Verify deployed valid/missing/invalid keys and atomic-registry replacement or revocation.
- [ ] Align sample schema and verify sample-to-provision-to-authenticate workflow.

## Resolution

- **Resolution Type**: `not-applicable`
- **Resolution Summary**: Open; executor correction and independent follow-up review pending.
- **Verification Evidence**: `.agent/reports/review/T-014.md`
- **Resolved By**: `none`
- **Resolved Date**: `none`

## Completion Criteria

- [ ] Acceptance criteria pass or a disposition is formally accepted.
- [ ] Resolution evidence is linked.
- [ ] Task and review records reflect the result.

## Forbidden Actions

- Do not close without correction evidence or accepted disposition.
- Preserve original review evidence when corrected.
- Do not claim an actual container smoke from static deployment inspection.

## Output Requirements

- Store runtime issue evidence in this governance record.
- Preserve stable finding IDs and link follow-up review.
