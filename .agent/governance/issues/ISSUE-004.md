---
id: issue-004
title: "ISSUE-004: RBAC, lọc tài liệu bị thay thế và routing nhạy cảm nằm sau /ask thật"
type: governance
domain: governance
module: issues
tags: [issue, dec-001, review-finding, F-03]
priority: 2
---
# ISSUE-004: RBAC, lọc tài liệu bị thay thế và routing nhạy cảm nằm sau /ask thật

## Usage Purpose

Theo dõi finding F-03 trong review baseline của B (`.agent/reports/review/REVIEW-DEC-001-B.md`), được A ghi nhận khi review chéo trong T-001.

## Record Metadata

- **Issue ID**: `ISSUE-004`
- **Title**: `RBAC, lọc tài liệu bị thay thế và routing nhạy cảm nằm sau /ask thật`
- **Owner**: `trong-hung`
- **Reporter**: `claude-code-a`
- **Status**: `triaged`
- **Issue Type**: `gap`
- **Priority**: `2`
- **Created Date**: `2026-10-26`
- **Target Date**: `2026-10-27`

## Description

`/ask` thật và xác thực thuộc M-001 (E-004, E-006), nhưng RBAC filter khi retrieve, loại tài liệu `superseded_by` và routing nhạy cảm nằm ở E-010 thuộc M-002. Lưu ý: T-016 đã ghi phạm vi 'Department + superseded filter inside the query', nên một phần đã có trong M-001; riêng routing nhạy cảm thì chưa.

## Impact

- **Affected Scope**: `.agent/planning/epics.md, docs/01-business/srs.md`
- **Severity**: `high`
- **User or Delivery Impact**: `Ở M-001, /ask thật có thể trả chunk khác phòng ban hoặc tài liệu bị thay thế, và gửi nội dung nhạy cảm lên cloud`

## Reproduction Evidence

- **Preconditions**: `main tại 0cbf93a`
- **Steps**: `đọc các file trong Affected Files`
- **Observed Result**: `như phần Description`
- **Expected Result**: `Mọi luồng dữ liệu thật/cloud ở M-001 đã có RBAC filter, lọc superseded và routing nhạy cảm; hoặc có change request điều chỉnh roadmap/phụ thuộc`
- **Evidence Paths**: `.agent/reports/review/REVIEW-DEC-001-B.md`

## Related Files

- **Affected Files**: `.agent/planning/epics.md, docs/01-business/srs.md`
- **Tasks or Epics**: `E-004, E-010, T-016, T-019`
- **Decisions**: `.agent/governance/decisions/DEC-001.md, .agent/governance/decisions/DEC-006.md`
- **Risks**: `none`
- **Blockers**: `none`

## Acceptance Criteria

- [ ] Nguyên nhân gốc hoặc hướng xử lý đã được ghi lại.
- [ ] Kết quả khắc phục được định nghĩa bằng điều kiện quan sát được.
- [ ] Cách kiểm tra regression được định nghĩa khi cần.
- [ ] Nếu cần đổi contract, SRS hoặc roadmap thì có change request đã duyệt.

## Resolution

- **Resolution Type**: `not-applicable`
- **Resolution Summary**: `Hướng xử lý: DEC-006 — giữ nguyên roadmap, M-001 chỉ dùng tài liệu classification public (filter trong T-016, kiểm ở T-019). Issue đóng khi T-016 và T-019 done kèm test.`
- **Verification Evidence**: `none`
- **Resolved By**: `none`
- **Resolved Date**: `none`

## Completion Criteria

- [ ] Acceptance criteria đạt hoặc đã có hướng xử lý được duyệt.
- [ ] Bằng chứng giải quyết đã được liên kết.
- [ ] Các record task, risk, blocker và regression liên quan đã được cập nhật.

## Forbidden Actions

- Không đóng issue khi chưa có bằng chứng giải quyết hoặc hướng xử lý được duyệt.
- Không sửa `openapi.yaml`, `contracts.py`, SRS hay roadmap khi chưa có change request đã duyệt.

## Output Requirements

- Lưu tại `.agent/governance/issues/ISSUE-004.md`.
- Giữ nguyên mọi heading của issue template.
