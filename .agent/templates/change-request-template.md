---
id: change-request-template
title: Change Request Template
type: governance
domain: governance
module: templates
tags: [change-request, template]
priority: 2
---
# Template Change Request

## Usage Purpose

Dùng template này để đề xuất, đánh giá, phê duyệt và truy vết một thay đổi đối với yêu cầu, contract, kiến trúc, roadmap hoặc phạm vi đã được chốt baseline.

## Record Metadata

- **Change Request ID**: `CR-<number>`
- **Title**: `<required>`
- **Owner**: `<required-person-or-agent-id>`
- **Proposer**: `<required-person-or-agent-id>`
- **Status**: `draft | proposed | under-review | approved | rejected | implementing | implemented | withdrawn | superseded`
- **Change Type**: `scope | requirement | contract | architecture | roadmap | process`
- **Priority**: `1 | 2 | 3 | 4 | 5`
- **Created Date**: `YYYY-MM-DD`
- **Decision Due Date**: `YYYY-MM-DD`

## Proposed Change

Mô tả chính xác trạng thái hiện tại và trạng thái mong muốn sau thay đổi.

## Justification

Nêu lý do cần thay đổi, dựa trên bằng chứng.

## Impact Assessment

- **Affected Baselines**: `<paths>`
- **Affected Epics or Tasks**: `<ids-or-none>`
- **Schedule Impact**: `<specific-impact-or-none>`
- **Cost or Resource Impact**: `<specific-impact-or-none>`
- **Security or Compliance Impact**: `<specific-impact-or-none>`
- **Compatibility or Migration Impact**: `<specific-impact-or-none>`

## Related Files

- **Affected Documents**: `<paths>`
- **Decisions**: `<paths-or-none>`
- **Risks**: `<paths-or-none>`
- **Issues or Blockers**: `<paths-or-none>`

## Approval

- **Decision**: `pending | approved | rejected`
- **Approver**: `<required-for-approved-or-rejected>`
- **Decision Date**: `YYYY-MM-DD`
- **Conditions**: `<conditions-or-none>`
- **Rationale**: `<required-for-approved-or-rejected>`

## Implementation Plan

- **Responsible Owner**: `<person-or-agent-id>`
- **Tasks**: `<task-ids>`
- **Validation Method**: `<checks>`
- **Rollback Method**: `<steps-or-not-applicable-with-reason>`

## Completion Criteria

- [ ] Phê duyệt được ghi lại trước khi sửa baseline.
- [ ] Các thay đổi đã duyệt được hiện thực và kiểm chứng.
- [ ] Mọi baseline bị ảnh hưởng và liên kết truy vết đã được cập nhật.
- [ ] Trạng thái là `implemented`, `rejected`, `withdrawn` hoặc `superseded`.

## Forbidden Actions

- Không sửa baseline khi quyết định còn là `pending` hoặc `rejected`.
- Không tự duyệt trừ khi mô hình governance cho phép rõ ràng.
- Không thay đổi phạm vi đã duyệt khi chưa có change request mới hoặc change request thay thế.
- Không bỏ qua phần đánh giá ảnh hưởng hay lý do phê duyệt.

## Output Requirements

- Lưu thành `.agent/governance/change-requests/CR-<number>.md`.
- Giữ nguyên mọi heading trong template này.
- Dùng link tương đối theo repo và đúng giá trị enum.
