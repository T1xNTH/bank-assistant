---
id: impl-t-033-pr98-fixes
title: T-033 PR 98 Review Fixes
type: report
domain: integrations
module: n8n
tags: [implementation, T-033, pr-98, review-fixes]
priority: 2
---
# T-033 PR 98 review fixes

## Record Metadata

- **Report ID**: `T-033-PR98-fixes`
- **Task ID**: `T-033`
- **Epic ID**: `E-012`
- **Owner**: `teammate-b`
- **Executor**: `codex-b`
- **Status**: `draft`
- **Report Date**: `2026-11-03`

## Scope

Address A's [review comment on fe30a4e](https://github.com/T1xNTH/bank-assistant/pull/98#issuecomment-6599776045).
This supplements `.agent/reports/implementation/T-033.md`; earlier evidence is retained.

## Changes Made

| Comment | Resolution |
|---|---|
| 1: Review email lacks question and recipient | Add Gửi tới and Câu hỏi from Validate intake before intent/needs_human/draft. Escape HTML text characters so original questions and drafts cannot inject markup. Two parametrized JS expression tests verify dynamic fields, ordering, preserved draft and escaped text. |
| 2: 25h workflow may be capped at 1h | Confirmed in pinned n8n 2.45.7: default maxTimeout=3600. Set EXECUTIONS_TIMEOUT_MAX=90000 in Compose; test budget covers 24h approval, 60 worst-case polls and delivery margin. |
| 3: HTTP failure notification | Document fail-closed behavior and Error Trigger follow-up owned by T-034. No error-handler scope added. |
| Lifecycle | Main still 7f4eb73 with T-032 in review. A's stated closure is not yet on main; task start still rejects the dependency. No T-032 closure or approval fabricated. |

## Verification Evidence

| Check | Result | Evidence |
|---|---|---|
| `pytest -q tests/unit/test_n8n_workflow.py` | passed | Final 21 passed in 2.00s, including upstream-decoder boundary and HTML-parser assertions on question and draft |
| Pinned n8n config without override | passed | maxTimeout=3600; effective min(90000,3600)=3600 |
| Pinned n8n config with EXECUTIONS_TIMEOUT_MAX=90000 | passed | maxTimeout=90000; effective timeout=90000 |
| `make check PY=python` | passed | Final production expression: 1092 passed, 2 skipped, 77 deselected, 1 upstream warning in 188.40s; Ruff and framework validation passed. The strengthened upstream-decoder test fixture was additionally rerun in the 21-case check above. |
| Unsafe named-entity negative control | passed | Regression test rejects replacing numeric entities with standard named entities before the pinned node's decoder |
| Live approval context and HTML safety | passed | Recipient, original question and citations present; literal HTML preserved in Mailpit; screenshot docs/11-integrations/evidence/T-033-review-context.png |
| Live approve/reject | passed | Approve sends cited reply to submitted recipient; rejection sends no customer email |
| Live container config | passed | Effective maxTimeout and workflow timeout both 90000 |
| Restore source after test | passed | Live nodes/connections/settings match source after ignoring n8n's auto-generated ordinary SMTP node webhook ID; 24h approval restored |
| Framework validation / diff check | passed | FRAMEWORK_VALIDATION_PASS; no whitespace errors |
| `python scripts/agent --actor codex-b task start T-033` | failed | dependencies not done: T-032; no lifecycle writes |

Configuration was inspected using ExecutionsConfig from the actual pinned Docker
image, both with and without the override. The pinned
[config source](https://github.com/n8n-io/n8n/blob/n8n%402.45.7/packages/%40n8n/config/src/configs/executions.config.ts)
and [runner](https://github.com/n8n-io/n8n/blob/n8n%402.45.7/packages/cli/src/workflow-runner.ts)
also confirm the clamp. No 24-hour wall-clock test is claimed.

Live tests exposed that the pinned node's helper named escapeHtml actually decodes
five named HTML entities before rendering. Initial raw/standard named-entity
versions allowed user tags into the approval HTML. The final expression uses
numeric text entities, which preserve literal question/draft text through that
helper. Unit HTMLParser checks reject actual tags in the generated message, and
the final SMTP/Chromium run verifies literal `<b>plain text</b>` in Mailpit.

An attempted simulation that changed only the execution table's startedAt did not
reproduce a real two-hour wait and failed its control expectation. It is excluded
as long-delay evidence. Timeout verification rests on the actual config values,
the pinned runner's cap calculation and the budget regression test; no claim of
two-hour or 24-hour wall-clock acceptance is made.

Local logs: output/t033-comments-live-final.log, output/t033-comments-check-final.log.

## Limitations and Follow-up

- ISSUE-029 remains open until A records T-032 closure on main. After merging that
  change, run the task start/report/verify/review-request CLI flow; no done claim.
- Independent approval of the updated commit remains pending.
- Legacy Windows Ruff 0.9.3 reports six pre-existing UP038 findings outside this
  change; changed-file lint passes. Full repository checks use the current Ruff in
  the backend QA image, matching CI's rules, without changing unrelated files.
- Earlier non-independent review/QA recheck reports remain local historical evidence
  for fe30a4e and are not new approval records.

## Related Files

- `.agent/execution/tasks/T-033.md`
- `.agent/governance/issues/ISSUE-029.md`
- `infrastructure/compose.yaml`
- `infrastructure/n8n/workflows/intake-to-reply.json`
- `tests/unit/test_n8n_workflow.py`
- `docs/11-integrations/n8n.md`

## Completion Outcome

Code fixes and final verification complete. Report stays draft because dependency
lifecycle reconciliation and the subsequent CLI report/review-request flow remain
pending. No self-approval, task completion, merge or T-034 implementation is claimed.
