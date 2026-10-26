---
id: issue-005
title: "ISSUE-005: Quyền truy cập thread, phạm vi người duyệt và giao dịch của agent chưa được định nghĩa"
type: governance
domain: governance
module: issues
tags: [issue, dec-001, review-finding, F-04]
priority: 2
---
# ISSUE-005: Quyền truy cập thread, phạm vi người duyệt và giao dịch của agent chưa được định nghĩa

## Usage Purpose

Theo dõi finding F-04 trong review baseline của B (`.agent/reports/review/REVIEW-DEC-001-B.md`), được A ghi nhận khi review chéo trong T-001.

## Record Metadata

- **Issue ID**: `ISSUE-005`
- **Title**: `Quyền truy cập thread, phạm vi người duyệt và giao dịch của agent chưa được định nghĩa`
- **Owner**: `teammate-b`
- **Reporter**: `claude-code-a`
- **Status**: `open`
- **Issue Type**: `gap`
- **Priority**: `2`
- **Created Date**: `2026-10-26`
- **Target Date**: `2026-11-02`

## Description

Contract chỉ nêu role `approver` và SQLite mở `mode=ro`, nhưng không định nghĩa ai sở hữu thread, approver được duyệt phạm vi nào, và user được xem giao dịch/tài khoản nào. Chế độ chỉ đọc không giới hạn được người xem.

## Impact

- **Affected Scope**: `docs/04-api/contract.md, docs/06-security/security-design.md, docs/05-database/schema.md`
- **Severity**: `high`
- **User or Delivery Impact**: `User có thể xem thread/giao dịch của người khác; approver có thể duyệt ngoài phạm vi`

## Reproduction Evidence

- **Preconditions**: `main tại 0cbf93a`
- **Steps**: `đọc các file trong Affected Files`
- **Observed Result**: `như phần Description`
- **Expected Result**: `Contract ghi rõ quyền sở hữu thread, phạm vi approver, quy tắc truy cập giao dịch; có test từ chối truy cập chéo user`
- **Evidence Paths**: `.agent/reports/review/REVIEW-DEC-001-B.md`

## Related Files

- **Affected Files**: `docs/04-api/contract.md, docs/06-security/security-design.md, docs/05-database/schema.md`
- **Tasks or Epics**: `0050`
- **Decisions**: `.agent/governance/decisions/DEC-001.md`
- **Risks**: `none`
- **Blockers**: `none`

## Acceptance Criteria

- [ ] Nguyên nhân gốc hoặc hướng xử lý đã được ghi lại.
- [ ] Kết quả khắc phục được định nghĩa bằng điều kiện quan sát được.
- [ ] Cách kiểm tra regression được định nghĩa khi cần.
- [ ] Nếu cần đổi contract, SRS hoặc roadmap thì có change request đã duyệt.

## Resolution

- **Resolution Type**: `not-applicable`
- **Resolution Summary**: `chưa giải quyết`
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

- Lưu tại `.agent/governance/issues/ISSUE-005.md`.
- Giữ nguyên mọi heading của issue template.
