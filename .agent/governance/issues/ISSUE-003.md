---
id: issue-003
title: "ISSUE-003: Job trong hàng chờ mất tín hiệu PII và quyền của user"
type: governance
domain: governance
module: issues
tags: [issue, dec-001, review-finding, F-02]
priority: 2
---
# ISSUE-003: Job trong hàng chờ mất tín hiệu PII và quyền của user

## Usage Purpose

Theo dõi finding F-02 trong review baseline của B (`.agent/reports/review/REVIEW-DEC-001-B.md`), được A ghi nhận khi review chéo trong T-001.

## Record Metadata

- **Issue ID**: `ISSUE-003`
- **Title**: `Job trong hàng chờ mất tín hiệu PII và quyền của user`
- **Owner**: `teammate-b`
- **Reporter**: `claude-code-a`
- **Status**: `triaged`
- **Issue Type**: `gap`
- **Priority**: `2`
- **Created Date**: `2026-10-26`
- **Target Date**: `2026-10-30`

## Description

Payload job chỉ gồm câu hỏi đã che + `user_id` (`docs/05-database/schema.md`, mục Redis), trong khi routing dựa trên loại PII phát hiện được. Chưa định nghĩa cách tín hiệu này còn giữ được sau khi che, hay cách worker lấy lại `User` có thẩm quyền.

## Impact

- **Affected Scope**: `docs/05-database/schema.md, docs/02-architecture/architecture.md`
- **Severity**: `high`
- **User or Delivery Impact**: `Job chứa PII có thể bị route sang cloud; worker có thể áp sai quyền department`

## Reproduction Evidence

- **Preconditions**: `main tại 0cbf93a`
- **Steps**: `đọc các file trong Affected Files`
- **Observed Result**: `như phần Description`
- **Expected Result**: `Payload có metadata routing an toàn (không chứa PII gốc); worker phân giải User từ nguồn chính thức; test: job có PII luôn local, RBAC đúng trong worker`
- **Evidence Paths**: `.agent/reports/review/REVIEW-DEC-001-B.md`

## Related Files

- **Affected Files**: `docs/05-database/schema.md, docs/02-architecture/architecture.md`
- **Tasks or Epics**: `E-009 (T-024, T-025), E-010`
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
- **Resolution Summary**: `Phương án A chọn (2026-10-27, checklist A-1): payload job thêm pii_types (chỉ tên loại) và force_local; worker phân giải User lại từ user_id qua kho key. Làm trong T-024/T-025; owner B xác nhận. Làm rõ của B (2026-10-27, https://github.com/caitoithap/bank-assistant/pull/29#issuecomment-6434139388), A đồng ý: baseline giữ nguyên "input có PII → local"; LLM cloud chỉ nhận văn bản đã che và không có PII trong input; cho văn bản đã che PII lên cloud là ngoại lệ routing, phải có change request được duyệt trước; force_local=true luôn được tôn trọng; giới hạn classification của CR-001 vẫn áp dụng.`
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

- Lưu tại `.agent/governance/issues/ISSUE-003.md`.
- Giữ nguyên mọi heading của issue template.
