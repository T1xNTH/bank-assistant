---
id: issue-007
title: "ISSUE-007: Chốt một process duy nhất ghi audit.db"
type: governance
domain: governance
module: issues
tags: [issue, t-001, review-observation, a-4]
priority: 2
---
# ISSUE-007: Chốt một process duy nhất ghi audit.db

## Usage Purpose

Theo dõi quan sát A-4 trong review baseline của A (`.agent/reports/review/T-001-A-baseline.md`). A đã đồng ý và chọn phương án ngày 2026-10-27.

## Record Metadata

- **Issue ID**: `ISSUE-007`
- **Title**: `Chốt một process duy nhất ghi audit.db`
- **Owner**: `teammate-b`
- **Reporter**: `claude-code-a`
- **Status**: `triaged`
- **Issue Type**: `gap`
- **Priority**: `3`
- **Created Date**: `2026-10-27`
- **Target Date**: `2026-10-30`

## Description

`data/audit.db` (SQLite) có thể được ghi từ cả `api` và `worker`. Kiến trúc chưa nói process nào ghi audit cho job.

## Impact

- **Affected Scope**: `data/audit.db, src/app/security/audit.py, src/app/queue/`
- **Severity**: `medium`
- **User or Delivery Impact**: `ghi đồng thời từ api và worker có thể khoá SQLite hoặc trùng/thiếu dòng audit`

## Reproduction Evidence

- **Preconditions**: `main tại 0cbf93a`
- **Steps**: `đọc các tài liệu trong Affected Scope`
- **Observed Result**: `như phần Description`
- **Expected Result**: `chỉ API ghi audit (lúc nhận job và lúc trả kết quả), worker không ghi; SQLite bật WAL; test mỗi request/job đúng một dòng audit`
- **Evidence Paths**: `.agent/reports/review/T-001-A-baseline.md`

## Related Files

- **Affected Files**: `data/audit.db, src/app/security/audit.py, src/app/queue/`
- **Tasks or Epics**: `E-006 (T-015), E-009 (T-024)`
- **Decisions**: `none`
- **Risks**: `none`
- **Blockers**: `none`

## Acceptance Criteria

- [x] Nguyên nhân gốc hoặc hướng xử lý đã được ghi lại.
- [ ] Kết quả khắc phục được định nghĩa bằng điều kiện quan sát được.
- [ ] Cách kiểm tra regression được định nghĩa khi cần.

## Resolution

- **Resolution Type**: `not-applicable`
- **Resolution Summary**: `Hướng xử lý A đã chọn: chỉ API ghi audit, bật WAL; áp dụng trong T-015 và T-024`
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

- Lưu tại `.agent/governance/issues/ISSUE-007.md`.
- Giữ nguyên mọi heading của issue template.
