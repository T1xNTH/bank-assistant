---
id: issue-019
title: "PR55-F03: Measure chat JSON compliance on the real cloud model"
type: governance
domain: platform
module: src/app/chat.py
tags: [issue, t-013, pr55-f03, cr-008, llm]
priority: 3
---
# ISSUE-019: Measure chat JSON compliance on the real cloud model

## Usage Purpose

Track the explicitly permitted follow-up from A's [PR55 review](https://github.com/caitoithap/bank-assistant/pull/55#issuecomment-6513438452).

## Record Metadata

- **Issue ID**: `ISSUE-019`
- **Title**: `Measure chat JSON compliance on the real cloud model`
- **Owner**: `teammate-b`
- **Reporter**: `trong-hung` via PR55-F03.
- **Status**: `open`
- **Issue Type**: `gap`
- **Priority**: `3`
- **Created Date**: `2026-10-30`
- **Target Date**: `none`; include in CR-008's pre-evaluation 5–10 question measurement.

## Description

POST /chat uses prompted JSON and strict application validation. Deterministic
tests establish safe rejection, but do not measure malformed-output frequency on
the real configured cloud-chat model. A explicitly allowed F03 as a follow-up.

## Impact

- **Affected Scope**: `T-013`, `E-005`, CR-008's real-model measurement.
- **Severity**: `low`
- **User or Delivery Impact**: A model may produce fenced JSON or commentary and cause 503 despite an otherwise useful answer.

## Reproduction Evidence

- **Preconditions**: Running authenticated LiteLLM gateway and configured real cloud provider.
- **Steps**: Submit a synthetic message to /chat with an LLM reply containing fenced JSON; compare with a valid JSON reply.
- **Observed Result**: Malformed output returns 503; valid output returns 200. Real-model frequency remains unmeasured. `docker ps` on 2026-10-30 returned no running containers, so no gateway/model smoke was attempted in this follow-up.
- **Expected Result**: Quantified real-model JSON compliance and an explicit decision about native structured output.
- **Evidence Paths**: `tests/api/test_chat.py`, `.agent/reports/implementation/T-013-PR55-fixes.md`.

## Related Files

- **Affected Files**: `src/app/chat.py`, `src/app/llm.py`, `src/app/contracts.py` only if a later approved protocol extension is required.
- **Tasks or Epics**: `T-013`, `E-005`, `E-008`.
- **Decisions**: `.agent/governance/change-requests/CR-008.md`.
- **Risks**: `RISK-003` (provider budget).
- **Blockers**: `none`; A classified this as a nonblocking follow-up.

## Acceptance Criteria

- [ ] Run 5–10 synthetic, non-PII messages through the actual /chat endpoint and configured real cloud-chat model within CR-008's budget. Record model/version, date, sample count, tokens and estimated cost.
- [ ] Record HTTP status for every sample; count 503 responses caused by malformed output separately from transport/provider/auth failures. Instrument validation counts without logging raw customer input, output or keys.
- [ ] If malformed-output 503 count is greater than zero, open a separately governed contract PR for LLM.chat response_format/json_schema support, requiring both owners' approval, as A requested.
- [ ] If the count is zero, record the limited sample result and retain application validation; do not claim universal model reliability.

## Resolution

- **Resolution Type**: `not-applicable` while measurement remains open.
- **Resolution Summary**: Pending; follow-up is authorized by A, not claimed complete.
- **Verification Evidence**: Existing deterministic API coverage only; no real provider result.
- **Resolved By**: `none`
- **Resolved Date**: `none`

## Completion Criteria

- [ ] Real measurement evidence and disposition are linked.
- [ ] Any required contract follow-up is tracked with both-owner approval.
- [ ] Task/review records link the final result.

## Forbidden Actions

- Do not label deterministic fake-gateway tests as real-model compliance measurements.
- Do not expose credentials or customer data, or broaden the existing LLM protocol without approval.

## Output Requirements

Preserve the source review and attach real measurement evidence before resolving.
