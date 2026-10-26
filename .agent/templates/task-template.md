---
id: task-template
title: Task Template
type: execution
domain: governance
module: templates
tags: [task, execution, template]
priority: 2
---
# Template Task

## Usage Purpose

Dùng template này để định nghĩa một đơn vị công việc có giới hạn rõ, kiểm chứng độc lập được, thuộc một epic đã được phép.

## Record Metadata

- **Task ID**: `T-<number>`
- **Epic ID**: `E-<number>`
- **Title**: `<required>`
- **Owner**: `<required-person-or-agent-id>`
- **Status**: `pending | in-progress | blocked | review | done | cancelled`
- **Created Date**: `YYYY-MM-DD`
- **Target Date**: `YYYY-MM-DD`
- **Priority**: `1 | 2 | 3 | 4 | 5`

## Objective

Nêu một sản phẩm duy nhất hoặc một thay đổi trạng thái mà task này phải tạo ra.

## Scope

### Bao gồm

- `<required-work-item>`

### Không bao gồm

- `<required-exclusion-or-none>`

## Preconditions

- [ ] Epic cha đang ở trạng thái `EPIC_IN_PROGRESS`.
- [ ] Đã có context package cần thiết.
- [ ] Đã có đủ dependency, phê duyệt và quyền truy cập.

## Related Files

- **Context Package**: `<path>`
- **Parent Epic**: `.agent/planning/epics.md#<epic-anchor>`
- **Decisions**: `<paths-or-none>`
- **Risks**: `<paths-or-none>`
- **Blockers**: `<paths-or-none>`
- **Change Requests**: `<paths-or-none>`

## Acceptance Criteria

- [ ] `<required-observable-condition>`
- [ ] Mỗi điều kiện đều có cách kiểm chứng được nêu rõ.

## Verification Requirements

- **Automated Checks**: `<commands-or-none-with-reason>`
- **Manual Checks**: `<steps-or-none-with-reason>`
- **Expected Evidence**: `<report-paths-logs-or-artifacts>`

## Completion Criteria

- [ ] Mọi acceptance criterion đều đạt.
- [ ] Các report bắt buộc được lưu trong `.agent/reports/`.
- [ ] Các commit hiện thực được ghi trong `.agent/intelligence/git-nexus/task-commit-map.md`.
- [ ] Current context và task board phản ánh trạng thái cuối cùng.

## Forbidden Actions

- Không làm việc ngoài phạm vi đã nêu.
- Không thực thi khi không có epic cha đã được phép.
- Không đánh dấu `done` trước khi kiểm chứng xong.
- Không bịa bằng chứng test, review, report hay commit.

## Output Requirements

- Đăng ký task trong `.agent/execution/task-board.md`.
- Giữ nguyên mọi heading trong template này.
- Thay mọi placeholder `<required...>`; chỉ dùng `none` ở chỗ được cho phép rõ ràng.
