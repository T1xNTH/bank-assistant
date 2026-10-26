---
id: blocker-template
title: Blocker Template
type: governance
domain: governance
module: templates
tags: [blocker, template]
priority: 2
---
# Template Blocker

## Usage Purpose

Dùng template này khi một epic hoặc task không thể tiếp tục vì một dependency, phê duyệt, quyền truy cập, quyết định hoặc lỗi cụ thể chưa được giải quyết.

## Record Metadata

- **Blocker ID**: `BLOCKER-<number>`
- **Title**: `<required>`
- **Owner**: `<required-person-or-agent-id>`
- **Reporter**: `<required-person-or-agent-id>`
- **Status**: `open | investigating | workaround-active | resolved | accepted | cancelled`
- **Blocker Type**: `dependency | approval | access | decision | defect | environment | external`
- **Priority**: `1 | 2 | 3 | 4 | 5`
- **Created Date**: `YYYY-MM-DD`
- **Target Resolution Date**: `YYYY-MM-DD`

## Blocking Condition

Nêu chính xác điều kiện đang cản trở tiến độ và bằng chứng xác nhận điều đó.

## Impact

- **Blocked Epics or Tasks**: `<ids>`
- **Blocked Deliverables**: `<outputs>`
- **Schedule or Quality Impact**: `<specific-impact>`

## Related Files

- **Affected Records**: `<paths>`
- **Issues**: `<paths-or-none>`
- **Decisions**: `<paths-or-none>`
- **Risks**: `<paths-or-none>`
- **Change Requests**: `<paths-or-none>`

## Resolution Plan

- **Required Action**: `<specific-action>`
- **Responsible Owner**: `<person-or-agent-id>`
- **Dependency or Approval**: `<identifier-or-none>`
- **Workaround**: `<bounded-workaround-or-none>`
- **Verification Method**: `<check>`

## Completion Criteria

- [ ] Điều kiện chặn không còn cản trở các công việc bị ảnh hưởng.
- [ ] Bằng chứng giải quyết đã được liên kết.
- [ ] Trạng thái các epic và task bị ảnh hưởng đã được cập nhật.
- [ ] Việc gỡ bỏ workaround được theo dõi khi có.

## Forbidden Actions

- Không đánh dấu `resolved` chỉ dựa trên một hành động mới được đề xuất.
- Không tiếp tục công việc bị chặn bằng một workaround chưa được phép.
- Không bỏ sót liên kết tới epic hay task bị ảnh hưởng.
- Không bịa bằng chứng giải quyết.

## Output Requirements

- Lưu thành `.agent/governance/blockers/BLOCKER-<number>.md`.
- Giữ nguyên mọi heading trong template này.
- Dùng link tương đối theo repo và đúng giá trị enum.
