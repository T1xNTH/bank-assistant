---
id: decision-template
title: Decision Template
type: governance
domain: governance
module: templates
tags: [decision, adr, template]
priority: 2
---
# Template Decision

## Usage Purpose

Dùng template này để ghi lại một quyết định quan trọng về kỹ thuật, sản phẩm, quy trình hoặc governance, cùng lý do có thể truy vết.

## Record Metadata

- **Decision ID**: `DEC-<number>`
- **Title**: `<required>`
- **Owner**: `<required-person-or-agent-id>`
- **Decision Makers**: `<required-person-or-role-ids>`
- **Status**: `proposed | under-review | accepted | rejected | superseded | deprecated`
- **Decision Type**: `architecture | product | process | governance | security | operations`
- **Created Date**: `YYYY-MM-DD`
- **Decision Date**: `YYYY-MM-DD | pending`

## Context

Nêu các điều kiện đã kiểm chứng, ràng buộc và vấn đề cần ra quyết định.

## Decision Drivers

- `<measurable-driver-or-constraint>`

## Options Considered

| Phương án | Lợi ích | Chi phí và rủi ro | Mức đáp ứng ràng buộc |
|---|---|---|---|
| `<option-name>` | `<specific-benefits>` | `<specific-costs-and-risks>` | `meets | partially-meets | does-not-meet` |

## Decision Outcome

- **Selected Option**: `<required-when-accepted>`
- **Rationale**: `<required-when-accepted-or-rejected>`
- **Effective Date**: `YYYY-MM-DD | pending`

## Consequences

- **Positive**: `<specific-consequences>`
- **Negative**: `<specific-consequences>`
- **Follow-up Work**: `<task-ids-or-none>`

## Related Files

- **Affected Documents**: `<paths>`
- **Epics or Tasks**: `<ids-or-none>`
- **Change Requests**: `<paths-or-none>`
- **Risks**: `<paths-or-none>`
- **Supersedes**: `<decision-paths-or-none>`
- **Superseded By**: `<decision-path-or-none>`

## Completion Criteria

- [ ] Bối cảnh, yếu tố quyết định và các phương án khả thi đã được ghi lại.
- [ ] Người ra quyết định và lý do đã được ghi lại.
- [ ] Công việc tiếp theo và tài liệu bị ảnh hưởng đã được liên kết.
- [ ] Quyết định đã chấp nhận được ánh xạ trong `.agent/intelligence/git-nexus/decision-commit-map.md` khi đã hiện thực.

## Forbidden Actions

- Không ghi một quyết định là `accepted` khi chưa xác định người ra quyết định.
- Không xoá các phương án bị loại hay hệ quả sau khi đã chấp nhận.
- Không âm thầm sửa một quyết định đã chấp nhận; hãy thay thế nó bằng một record mới.
- Không tuyên bố đã hiện thực khi chưa có bằng chứng commit hoặc report.

## Output Requirements

- Lưu thành `.agent/governance/decisions/DEC-<number>.md`.
- Giữ nguyên mọi heading và cột bảng trong template này.
- Dùng link tương đối theo repo và đúng giá trị enum.
