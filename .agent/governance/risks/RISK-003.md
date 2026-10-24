---
id: risk-003
title: Gemini free-tier rate limits
type: governance
domain: governance
module: risks
tags: [risk, external]
priority: 2
---
# RISK-003: Gemini free-tier rate limits

## Record Metadata

- **Risk ID**: `RISK-003`
- **Title**: `Gemini free-tier rate limits`
- **Owner**: `teammate-b`
- **Status**: `identified`
- **Category**: `external`
- **Probability**: `high`
- **Impact**: `medium`
- **Priority**: `2`
- **Created Date**: `2026-10-24`
- **Review Date**: `2026-10-28`

## Risk Statement

If Gemini returns 429 under eval or demo load, then runs fail, resulting in missing eval numbers and failed demos.

## Exposure Assessment

- **Affected Scope**: `E-008, E-009, E-014`
- **Impact Description**: schedule slip against the 10-day MVP window.
- **Detection Signals**: 429 errors in logs
- **Assumptions**: `none`

## Related Files

- **Epics or Tasks**: `E-008, E-009, E-014`
- **Decisions**: `none`
- **Issues or Blockers**: `none`
- **Change Requests**: `none`
- **Evidence**: `none`

## Response Plan

- **Strategy**: `mitigate`
- **Mitigation Actions**: Queue with token-bucket worker and backoff (E-009); judge with low concurrency; cache eval answers.
- **Contingency Actions**: Fall back to local model for non-judge calls.
- **Trigger Threshold**: > 5 % calls with 429
- **Responsible Owner**: `teammate-b`

## Review Record

- **Last Reviewed Date**: `2026-10-24`
- **Reviewed By**: `trong-hung`
- **Probability Change**: `unchanged`
- **Impact Change**: `unchanged`
- **Review Evidence**: `none`

## Completion Criteria

- [ ] The risk is eliminated, accepted by an authorized owner, transferred, or converted to an issue after realization.
- [ ] Final status and supporting evidence are recorded.
- [ ] Related tasks, blockers, issues, and decisions are updated.

## Forbidden Actions

- Do not close a risk solely because its review date passed.
- Do not accept a high or critical risk without an identified authorized owner.
- Do not use vague triggers or unowned mitigation actions.
- Do not delete prior assessments when exposure changes.

## Output Requirements

- Save as `.agent/governance/risks/RISK-003.md`.
- Preserve every heading in this template.
- Use repository-relative links and exact enum values.
