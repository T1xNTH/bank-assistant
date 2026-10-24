---
id: risk-001
title: Docker not installed on development machines
type: governance
domain: governance
module: risks
tags: [risk, delivery]
priority: 2
---
# RISK-001: Docker not installed on development machines

## Record Metadata

- **Risk ID**: `RISK-001`
- **Title**: `Docker not installed on development machines`
- **Owner**: `teammate-b`
- **Status**: `identified`
- **Category**: `delivery`
- **Probability**: `high`
- **Impact**: `high`
- **Priority**: `2`
- **Created Date**: `2026-10-24`
- **Review Date**: `2026-10-28`

## Risk Statement

If Docker is not installed on N1, then compose-based epics cannot start, resulting in a delay of E-002 and every dependent epic.

## Exposure Assessment

- **Affected Scope**: `E-002, E-005, E-009`
- **Impact Description**: schedule slip against the 10-day MVP window.
- **Detection Signals**: `docker version` fails on N1 afternoon
- **Assumptions**: `none`

## Related Files

- **Epics or Tasks**: `E-002, E-005, E-009`
- **Decisions**: `none`
- **Issues or Blockers**: `none`
- **Change Requests**: `none`
- **Evidence**: `none`

## Response Plan

- **Strategy**: `mitigate`
- **Mitigation Actions**: Install Docker Engine + compose plugin first thing N1 (both machines).
- **Contingency Actions**: Run Qdrant/Redis binaries natively; keep fakes for API work.
- **Trigger Threshold**: Docker not working by N1 end
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

- Save as `.agent/governance/risks/RISK-001.md`.
- Preserve every heading in this template.
- Use repository-relative links and exact enum values.
