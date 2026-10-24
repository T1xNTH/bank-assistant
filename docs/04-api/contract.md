---
id: project-contract
title: Project Contract Intake
type: reference
domain: api
module: repository
tags: [contract, interface, intake]
priority: 1
---
# Project Contract Intake

## Purpose

Track ingestion and validation of the authoritative project contract, including external interfaces and binding delivery constraints.

## Input Status

- **Status**: `missing`
- **Authority**: `not-established`
- **Source Artifact**: `not-provided`
- **Ingested Date**: `not-applicable`
- **Validated By**: `not-assigned`

## Required Content

- Contract scope, parties, obligations, and exclusions
- Interface or API contracts with stable identifiers
- Data, compatibility, security, and compliance obligations
- Service levels, acceptance conditions, and change-control terms
- Versioning, ownership, approval, and effective-date information

## Validation Result

No contract artifact was found in the onboarding input or repository. Contractual and interface obligations cannot be baselined.

## Related Files

- Blocker: `.agent/governance/blockers/BLOCKER-002.md`
- Roadmap: `.agent/planning/roadmap.md`
- Epic registry: `.agent/planning/epics.md`

## Forbidden Actions

- Do not invent interface fields, service levels, obligations, or approval terms.
- Do not mark this document authoritative until the source artifact is provided and validated.
- Do not create implementation tasks from this intake record.
