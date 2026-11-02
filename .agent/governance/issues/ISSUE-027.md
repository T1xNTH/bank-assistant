---
id: issue-027
title: Per-key rate limit for /chat and /ask
type: governance
domain: platform
module: api
tags: [issue, rate-limit, T-013, T-025]
priority: 2
---
# ISSUE-027: Per-key rate limit missing on /chat and /ask

## Usage Purpose

Track review finding F-01 of T-013 and T-025.

## Record Metadata

- **Issue ID**: `ISSUE-027`
- **Title**: Per-key rate limit for /chat and /ask
- **Owner**: `teammate-b`
- **Reporter**: `claude-review-a`
- **Status**: `open`
- **Issue Type**: `gap`
- **Priority**: `2`
- **Created Date**: `2026-11-02`
- **Target Date**: `2026-11-06`

## Description

OpenAPI declares 429 `RateLimited` (with Retry-After) for POST /chat and POST /ask, but only POST /ask/jobs applies the per-key token bucket (`src/app/queue/jobs.py`). One key can call /chat or /ask without limit and exhaust the shared Gemini quota.

## Impact

- **Affected Scope**: `POST /chat`, `POST /ask`
- **Severity**: `medium`
- **User or Delivery Impact**: Contract promise not met; RISK-003 (Gemini 429) more likely under misuse.

## Reproduction Evidence

- **Preconditions**: Valid API key; any backend.
- **Steps**: Send more than API_KEY_RPM requests per minute to /chat.
- **Observed Result**: All requests are processed; none returns 429.
- **Expected Result**: Requests beyond the bucket return 429 with Retry-After, as on /ask/jobs.
- **Evidence Paths**: `.agent/reports/review/T-013.md`, `.agent/reports/review/T-025.md`

## Related Files

- **Affected Files**: `src/app/main.py`, `src/app/queue/limits.py`, `tests/api/test_chat.py`, `tests/api/test_ask*.py`
- **Tasks or Epics**: `T-013`, `T-025`, `E-005`, `E-009`
- **Decisions**: `DEC-001`
- **Risks**: `none`
- **Blockers**: `none`

## Acceptance Criteria

- [ ] /chat and /ask reuse TokenBucket keyed by the API-key digest.
- [ ] API tests cover 429 + Retry-After on both endpoints.
- [ ] `make check` passes.

## Resolution

Open. Recorded by the post-merge review of T-013/T-025; no fix is claimed.

## Completion Criteria

- [ ] Link the fix PR and verification evidence.
- [ ] Update this record only after the fix is merged.

## Forbidden Actions

Do not close this issue without a test that demonstrates the fix.

## Output Requirements

Keep the follow-up traceable to the T-013 and T-025 review reports.
