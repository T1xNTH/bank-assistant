---
id: issue-028
title: Audit rows for /chat lack user and masked message
type: governance
domain: platform
module: api
tags: [issue, audit, T-013, FR-05]
priority: 2
---
# ISSUE-028: /chat audit rows lack user and question

## Usage Purpose

Track review finding F-02 of T-013.

## Record Metadata

- **Issue ID**: `ISSUE-028`
- **Title**: Audit rows for /chat lack user and masked message
- **Owner**: `teammate-b`
- **Reporter**: `claude-review-a`
- **Status**: `open`
- **Issue Type**: `gap`
- **Priority**: `2`
- **Created Date**: `2026-11-02`
- **Target Date**: `2026-11-06`

## Description

`chat()` in `src/app/main.py` does not set `request.state.audit_user` or `audit_question` (as `ask()` does), so the audit middleware writes /chat rows with NULL user_id, department and question_masked. FR-05 requires auditing who asked what and when.

## Impact

- **Affected Scope**: `POST /chat`, `data/audit.db`
- **Severity**: `medium`
- **User or Delivery Impact**: Audit trail incomplete for /chat requests.

## Reproduction Evidence

- **Preconditions**: Valid API key; audit enabled.
- **Steps**: Call POST /chat, then read the latest row of the audit table.
- **Observed Result**: user_id, department and question_masked are NULL.
- **Expected Result**: Row holds the caller's user_id, department and the masked message.
- **Evidence Paths**: `.agent/reports/review/T-013.md`, `.agent/reports/review/T-025.md`

## Related Files

- **Affected Files**: `src/app/main.py`, `tests/api/test_chat.py`
- **Tasks or Epics**: `T-013`, `E-005`, `FR-05`; fix in `T-037` (`E-013`)
- **Decisions**: `DEC-001`
- **Risks**: `none`
- **Blockers**: `none`

## Acceptance Criteria

- [ ] chat() sets audit_user and the masked audit_question before calling the LLM.
- [ ] An API test asserts the /chat audit row.
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
