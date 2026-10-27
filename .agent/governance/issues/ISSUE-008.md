---
id: issue-008
title: "ISSUE-008: Chưa có ADR cho 4 quyết định kiến trúc chính"
type: governance
domain: governance
module: issues
tags: [issue, t-001, review-observation, a-5]
priority: 2
---
# ISSUE-008: Chưa có ADR cho 4 quyết định kiến trúc chính

## Usage Purpose

Theo dõi quan sát A-5 trong review baseline của A (`.agent/reports/review/T-001-A-baseline.md`). A đã đồng ý và chọn phương án ngày 2026-10-27.

## Record Metadata

- **Issue ID**: `ISSUE-008`
- **Title**: `Chưa có ADR cho 4 quyết định kiến trúc chính`
- **Owner**: `trong-hung`
- **Reporter**: `claude-code-a`
- **Status**: `triaged`
- **Issue Type**: `gap`
- **Priority**: `3`
- **Created Date**: `2026-10-27`
- **Target Date**: `2026-11-06`

## Description

Mục "Các quyết định chính" của kiến trúc nhắc 4 ADR (Qdrant hybrid, routing lai, RBAC dạng payload filter, hàng chờ RQ) nhưng chưa có decision record nào (DEC-001..006 là quyết định quy trình).

## Impact

- **Affected Scope**: `docs/02-architecture/architecture.md, .agent/governance/decisions/`
- **Severity**: `medium`
- **User or Delivery Impact**: `FR-12 yêu cầu ADR; thiếu thì không truy vết được lý do thiết kế`

## Reproduction Evidence

- **Preconditions**: `main tại 0cbf93a`
- **Steps**: `đọc các tài liệu trong Affected Scope`
- **Observed Result**: `như phần Description`
- **Expected Result**: `4 decision record ADR, mỗi cái có bối cảnh, phương án, lý do và số liệu nếu có`
- **Evidence Paths**: `.agent/reports/review/T-001-A-baseline.md`

## Related Files

- **Affected Files**: `docs/02-architecture/architecture.md, .agent/governance/decisions/`
- **Tasks or Epics**: `E-016`
- **Decisions**: `none`
- **Risks**: `none`
- **Blockers**: `none`

## Acceptance Criteria

- [x] Nguyên nhân gốc hoặc hướng xử lý đã được ghi lại.
- [ ] Kết quả khắc phục được định nghĩa bằng điều kiện quan sát được.
- [ ] Cách kiểm tra regression được định nghĩa khi cần.

## Resolution

- **Resolution Type**: `not-applicable`
- **Resolution Summary**: `Hướng xử lý A đã chọn: viết 4 ADR ở E-016 (FR-12), dùng số liệu từ eval E-008/E-014`
- **Verification Evidence**: `none`
- **Resolved By**: `none`
- **Resolved Date**: `none`

## Completion Criteria

- [ ] Acceptance criteria đạt hoặc đã có hướng xử lý được duyệt.
- [ ] Bằng chứng giải quyết đã được liên kết.
- [ ] Các record task, risk, blocker và regression liên quan đã được cập nhật.

## Forbidden Actions

- Không đóng issue khi chưa có bằng chứng giải quyết.
- Không sửa SRS, contract hay kiến trúc đã duyệt khi chưa có change request đã duyệt.

## Output Requirements

- Lưu tại `.agent/governance/issues/ISSUE-008.md`.
- Giữ nguyên mọi heading của issue template.
