---
id: risk-004
title: Agent token limits interrupt execution
type: governance
domain: governance
module: risks
tags: [risk, delivery]
priority: 2
---
# RISK-004: Agent token limits interrupt execution

## Record Metadata

- **Risk ID**: `RISK-004`
- **Title**: `Agent token limits interrupt execution`
- **Owner**: `trong-hung`
- **Status**: `identified`
- **Category**: `delivery`
- **Probability**: `medium`
- **Impact**: `medium`
- **Priority**: `2`
- **Created Date**: `2026-10-24`
- **Review Date**: `2026-10-28`

## Risk Statement

If Claude Code usage limits are hit mid-task, then work stops, resulting in idle hours and half-finished branches.

## Exposure Assessment

- **Affected Scope**: `all epics`
- **Impact Description**: schedule slip against the 10-day MVP window.
- **Detection Signals**: usage warnings at 80 %
- **Assumptions**: `none`

## Related Files

- **Epics or Tasks**: `all epics`
- **Decisions**: `none`
- **Issues or Blockers**: `none`
- **Change Requests**: `none`
- **Evidence**: `none`

## Response Plan

- **Strategy**: `mitigate`
- **Mitigation Actions**: Tasks ≤ half a day; commit WIP and update implementation report before limits; partner can continue.
- **Contingency Actions**: Swap tasks between A and B.
- **Trigger Threshold**: usage > 80 % of window
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

- Save as `.agent/governance/risks/RISK-004.md`.
- Preserve every heading in this template.
- Use repository-relative links and exact enum values.
