---
id: issue-026
title: Document job polling dependency-unavailable response in OpenAPI
type: governance
domain: platform
module: queue
tags: [issue, contract, T-024, pr-63]
priority: 3
---
# ISSUE-026: Missing OpenAPI 503 for job polling

## Usage Purpose

Track the non-blocking contract follow-up requested in PR 63 re-review.

## Record Metadata

- **Issue ID**: `ISSUE-026`
- **Title**: Document job polling dependency-unavailable response in OpenAPI
- **Owner**: `teammate-b`
- **Reporter**: `codex`
- **Status**: `open`
- **Issue Type**: `gap`
- **Priority**: `3`
- **Created Date**: `2026-10-31`
- **Target Date**: `none`

## Description

GET `/ask/jobs/{job_id}` returns 503 when Redis is unavailable, but the approved
OpenAPI lists only 200, 401 and 404 for this operation. Its implementation already
returns the shared SERVICE_UNAVAILABLE error envelope.

## Impact

- **Affected Scope**: `docs/04-api/openapi.yaml`, job polling clients.
- **Severity**: `low`
- **User or Delivery Impact**: Generated clients cannot discover this dependency error from the contract.

## Reproduction Evidence

- **Preconditions**: Authenticated polling request; Redis unavailable.
- **Steps**: Run `tests/api/test_jobs.py::test_redis_unavailable_returns_503` for GET and inspect OpenAPI.
- **Observed Result**: API returns 503; contract omits it.
- **Expected Result**: Contract declares 503 using `#/components/responses/Unavailable`.
- **Evidence Paths**: [PR 63 re-review](https://github.com/T1xNTH/bank-assistant/pull/63#issuecomment-6540076503).

## Related Files

- **Affected Files**: `docs/04-api/openapi.yaml`, `src/app/queue/jobs.py`, `tests/api/test_jobs.py`
- **Tasks or Epics**: `T-024`, `E-009`
- **Decisions**: `none`
- **Risks**: `none`
- **Blockers**: `none`

## Acceptance Criteria

- [ ] Create and obtain approval for a contract change request.
- [ ] In a separate contract PR, add GET's 503 response referencing `Unavailable`.
- [ ] Validate OpenAPI and the existing Redis-unavailable API regression.
- [ ] Obtain both owners' approval as required by the team workflow.

## Resolution

Open; no contract change or approval is claimed. This issue records the follow-up
without changing the approved contract in the implementation PR.

## Completion Criteria

- [ ] Link the approved change request, contract PR and verification evidence.
- [ ] Update this record only after the contract follow-up is complete.

## Forbidden Actions

Do not treat the review's request to track the gap as approval to change the contract.

## Output Requirements

Keep the contract follow-up traceable to T-024 and PR 63.
