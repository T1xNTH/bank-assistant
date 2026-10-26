---
id: epic-template
title: Epic Template
type: planning
domain: governance
module: templates
tags: [epic, planning, template]
priority: 2
---
# Template Epic

## Usage Purpose

Dùng template này để định nghĩa một epic hướng tới kết quả, trước khi bắt đầu tách task.

## Record Metadata

- **Epic ID**: `E-<number>`
- **Title**: `<required>`
- **Owner**: `<required-person-or-agent-id>`
- **Status**: `EPIC_PROPOSED | EPIC_READY | EPIC_IN_PROGRESS | EPIC_BLOCKED | EPIC_DONE | EPIC_CANCELLED`
- **Milestone ID**: `M-<number>`
- **Created Date**: `YYYY-MM-DD`
- **Target Date**: `YYYY-MM-DD`
- **Priority**: `1 | 2 | 3 | 4 | 5`

## Objective

Nêu một kết quả đo lường được và lý do cần đạt kết quả đó.

## Scope

### Bao gồm

- `<required-scope-item>`

### Không bao gồm

- `<required-exclusion-or-none>`

## Dependencies

- **Depends On**: `<epic-or-milestone-ids-or-none>`
- **Blocked By**: `<blocker-ids-or-none>`

## Related Files

- **Roadmap**: `.agent/planning/roadmap.md`
- **Milestones**: `.agent/planning/milestones.md`
- **Dependency Graph**: `.agent/planning/dependency-graph.md`
- **Decisions**: `<paths-or-none>`
- **Risks**: `<paths-or-none>`
- **Change Requests**: `<paths-or-none>`

## Acceptance Criteria

- [ ] Mỗi tiêu chí đều quan sát được và kiểm thử được.
- [ ] Ranh giới phạm vi được nêu rõ.
- [ ] Dependency và governance link đang cập nhật.
- [ ] Report bắt buộc và bằng chứng kiểm chứng đã được xác định.

## Task Expansion Rules

- Chỉ tạo task khi trạng thái là `EPIC_READY`.
- Chỉ bắt đầu thực thi task khi trạng thái là `EPIC_IN_PROGRESS`.
- Mọi task phải tham chiếu tới ID của epic này.

## Completion Criteria

- [ ] Mọi task liên kết đều `done` hoặc đã được huỷ chính thức.
- [ ] Acceptance criteria đã được kiểm chứng với bằng chứng liên kết.
- [ ] Có đủ implementation, review và QA report bắt buộc.
- [ ] Blocker và risk còn mở đều có hướng xử lý rõ ràng.

## Forbidden Actions

- Không tách task khi trạng thái là `EPIC_PROPOSED`.
- Không đánh dấu epic `EPIC_DONE` khi acceptance criteria chưa đạt.
- Không đổi phạm vi đã chốt baseline khi chưa có change request đã duyệt.
- Không ghi liên kết, bằng chứng hay trạng thái hoàn thành bịa đặt.

## Output Requirements

- Lưu record hoàn chỉnh trong `.agent/planning/epics.md` hoặc registry epic được dự án duyệt.
- Giữ nguyên mọi heading trong template này.
- Thay mọi placeholder `<required...>`; chỉ dùng `none` ở chỗ được cho phép rõ ràng.
