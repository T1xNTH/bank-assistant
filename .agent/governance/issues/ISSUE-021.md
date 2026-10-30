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
- **Status**: `open`
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
- [ ] Fix: both reproduced inputs fully mask the phone and return PHONE_NUMBER.
- [ ] Add public mask_text regressions for phones before amounts/accounts, retaining or conservatively justifying existing invalid-length and boundary cases.

## Resolution

- **Resolution Type**: `not-applicable`
- **Resolution Summary**: `Open; contextual suffix check conflates independent numeric word with phone continuation. Fix segmentation/boundaries conservatively and add public mask_text regression cases.`
- **Verification Evidence**: `Pending fix; independent reviewer reproduction in T-020 review report.`
- **Resolved By**: `none`
- **Resolved Date**: `none`

## Completion Criteria

- [ ] Acceptance criteria đạt hoặc đã có hướng xử lý được duyệt.
- [ ] Bằng chứng giải quyết đã được liên kết.
- [ ] Các record task, risk, blocker và regression liên quan đã được cập nhật.

## Forbidden Actions

- Không đóng issue khi chưa có bằng chứng giải quyết hoặc hướng xử lý được duyệt.
- Không xoá lịch sử khi trạng thái hay owner thay đổi.
- Không gộp các vấn đề không liên quan vào một issue.
- Không bịa bằng chứng tái hiện hay kiểm chứng.

## Output Requirements

- Lưu thành `.agent/governance/issues/ISSUE-<number>.md`.
- Giữ nguyên mọi heading trong template này.
- Dùng link tương đối theo repo và đúng giá trị enum.
