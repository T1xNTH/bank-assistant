---
id: issue-template
title: Issue Template
type: governance
domain: governance
module: templates
tags: [issue, template]
priority: 3
---
# Template Issue

## Usage Purpose

Dùng template này để ghi lại một lỗi, khoảng trống, điểm không nhất quán hoặc mối lo cần xử lý và được theo dõi.

## Record Metadata

- **Issue ID**: `ISSUE-<number>`
- **Title**: `<required>`
- **Owner**: `<required-person-or-agent-id>`
- **Reporter**: `<required-person-or-agent-id>`
- **Status**: `open | triaged | in-progress | blocked | resolved | closed | rejected`
- **Issue Type**: `defect | gap | inconsistency | improvement | process`
- **Priority**: `1 | 2 | 3 | 4 | 5`
- **Created Date**: `YYYY-MM-DD`
- **Target Date**: `YYYY-MM-DD | none`

## Description

Mô tả tình trạng quan sát được một cách khách quan và tái hiện được.

## Impact

- **Affected Scope**: `<modules-documents-or-processes>`
- **Severity**: `critical | high | medium | low`
- **User or Delivery Impact**: `<specific-impact>`

## Reproduction Evidence

- **Preconditions**: `<conditions-or-not-applicable>`
- **Steps**: `<ordered-steps-or-not-applicable>`
- **Observed Result**: `<result>`
- **Expected Result**: `<result>`
- **Evidence Paths**: `<paths-or-none>`

## Related Files

- **Affected Files**: `<paths>`
- **Tasks or Epics**: `<ids-or-none>`
- **Decisions**: `<paths-or-none>`
- **Risks**: `<paths-or-none>`
- **Blockers**: `<paths-or-none>`

## Acceptance Criteria

- [ ] Nguyên nhân gốc hoặc hướng xử lý đã được ghi lại.
- [ ] Kết quả khắc phục được định nghĩa bằng điều kiện quan sát được.
- [ ] Cách kiểm tra regression được định nghĩa khi cần.

## Resolution

- **Resolution Type**: `fixed | duplicate | rejected | accepted-risk | superseded | not-applicable`
- **Resolution Summary**: `<required-before-resolved>`
- **Verification Evidence**: `<paths-required-before-closed>`
- **Resolved By**: `<person-or-agent-id>`
- **Resolved Date**: `YYYY-MM-DD`

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
