---
id: risk-002
title: CPU-only inference too slow
type: governance
domain: governance
module: risks
tags: [risk, technical]
priority: 2
---
# RISK-002: CPU-only inference too slow

## Record Metadata

- **Risk ID**: `RISK-002`
- **Title**: `CPU-only inference too slow`
- **Owner**: `trong-hung`
- **Status**: `identified`
- **Category**: `technical`
- **Probability**: `high`
- **Impact**: `medium`
- **Priority**: `2`
- **Created Date**: `2026-10-24`
- **Review Date**: `2026-10-28`

## Risk Statement

If bge-m3, reranker and Qwen2.5 run on CPU only, then ingest and local answers may be too slow, resulting in long ingest runs and p95 above NFR-08 for local route.

## Exposure Assessment

- **Affected Scope**: `E-003, E-004, E-010`
- **Impact Description**: schedule slip against the 10-day MVP window.
- **Detection Signals**: ingest > 60 min for 30 PDFs; local answer > 60 s
- **Assumptions**: `none`

## Related Files

- **Epics or Tasks**: `E-003, E-004, E-010`
- **Decisions**: `none`
- **Issues or Blockers**: `none`
- **Change Requests**: `none`
- **Evidence**: `none`

## Response Plan

- **Strategy**: `mitigate`
- **Mitigation Actions**: Run ingest in background once and snapshot Qdrant; use qwen2.5:3b; cache models; NFR-08 measured on cloud route.
- **Contingency Actions**: Reduce corpus for CI; document local-route latency.
- **Trigger Threshold**: measured timings in eval report
- **Responsible Owner**: `trong-hung`

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

- Save as `.agent/governance/risks/RISK-002.md`.
- Preserve every heading in this template.
- Use repository-relative links and exact enum values.
