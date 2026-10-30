---
id: issue-021
title: Complete VN phone can remain unmasked before an independent number
type: governance
domain: governance
module: pii
tags: [issue, t-020, e-007, security, pii]
priority: 1
---
# ISSUE-021: Complete VN phone can remain unmasked before an independent number

## Usage Purpose

Dùng template này để ghi lại một lỗi, khoảng trống, điểm không nhất quán hoặc mối lo cần xử lý và được theo dõi.

## Record Metadata

- **Issue ID**: `ISSUE-021`
- **Title**: `Complete VN phone can remain unmasked before an independent number`
- **Owner**: `teammate-b`
- **Reporter**: `codex-review-a`
- **Status**: `resolved`
- **Issue Type**: `defect`
- **Priority**: `1`
- **Created Date**: `2026-10-30`
- **Target Date**: `none`

## Description

F-T020-01: pii.py:23 rejects every phone span followed by a space and digit. A valid complete phone followed by an independent amount can therefore remain fully visible. The account recognizer cannot recover a contiguous +84 phone because its left boundary rejects plus; formatted segments can be too short for accounts.

## Impact

- **Affected Scope**: `src/app/security/pii.py; future T-021 redaction and sensitive routing`
- **Severity**: `high`
- **User or Delivery Impact**: `Raw complete phone may survive masking with no PII type, invalidating the redaction guarantee. T-021 is not yet integrated.`

## Reproduction Evidence

- **Preconditions**: `WSL Python 3.12; presidio-analyzer 2.2.366; PYTHONPATH=src`
- **Steps**: `Call mask_text("+84900000001 100 VND") and mask_text("0900 000 001 100 VND"). Synthetic values only.`
- **Observed Result**: `Both return original text and []; international phone followed by account also leaves full phone intact.`
- **Expected Result**: `Fully mask valid phone and include PHONE_NUMBER while treating independent following amount/account safely.`
- **Evidence Paths**: `.agent/reports/review/T-020.md#findings`

## Related Files

- **Affected Files**: `src/app/security/pii.py:23; tests/security/test_pii.py:36-59`
- **Tasks or Epics**: `T-020; E-007`
- **Decisions**: `.agent/governance/decisions/DEC-001.md`
- **Risks**: `none`
- **Blockers**: `none`

## Acceptance Criteria

- [x] Root cause identified: suffix check conflates independent numeric words with phone extensions.
- [x] Fix: both reproduced inputs fully mask the phone and return PHONE_NUMBER.
- [x] Add public mask_text regressions for phones before amounts/accounts, retaining or conservatively justifying existing invalid-length and boundary cases.

## Resolution

- **Resolution Type**: `fixed`
- **Resolution Summary**: `Fixed by codex-b in 9e7947c; suffix suppression removed and conservative ambiguity policy documented. Independently verified by codex-review-a. Original finding and pre-fix reproduction above remain historical evidence.`
- **Verification Evidence**: `.agent/reports/review/T-020-F01.md: 68 focused tests passed; independent 216-case matrix plus six boundary negatives and exact original reproductions passed. Parent full make check 406 passed, 24 deselected. Implementation supplement T-020-F01.md.`
- **Resolved By**: `codex-review-a (verification); codex-b (implementation)`
- **Resolved Date**: `2026-10-30`

## Completion Criteria

- [x] Acceptance criteria đạt hoặc đã có hướng xử lý được duyệt.
- [x] Bằng chứng giải quyết đã được liên kết.
- [x] Các record task, risk, blocker và regression liên quan đã được cập nhật.

## Forbidden Actions

- Không đóng issue khi chưa có bằng chứng giải quyết hoặc hướng xử lý được duyệt.
- Không xoá lịch sử khi trạng thái hay owner thay đổi.
- Không gộp các vấn đề không liên quan vào một issue.
- Không bịa bằng chứng tái hiện hay kiểm chứng.

## Output Requirements

- Lưu thành `.agent/governance/issues/ISSUE-<number>.md`.
- Giữ nguyên mọi heading trong template này.
- Dùng link tương đối theo repo và đúng giá trị enum.

## Resolution History

- 2026-10-30: codex-review-a opened ISSUE-021 from F-T020-01 against original 2a7f7a4. Original disclosure evidence retained above.
- 2026-10-30: user authorized correction; codex-b committed 9e7947c. Independent codex-review-a verified and resolved the defect with supplemental technical APPROVED report T-020-F01. This does not fulfill the separate Claude/peer task completion gates.
