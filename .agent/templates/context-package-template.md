---
id: context-package-template
title: Context Package Template
type: execution
domain: agents
module: templates
tags: [context, retrieval, template]
priority: 1
---
# Template Context Package

## Usage Purpose

Dùng template này để cung cấp lượng ngữ cảnh chính thức tối thiểu cần để thực thi một epic hoặc task mà không phải truy xuất toàn bộ repo.

## Record Metadata

- **Context Package ID**: `CTX-<number>`
- **Title**: `<required>`
- **Owner**: `<required-person-or-agent-id>`
- **Status**: `draft | ready | stale | archived`
- **Target Type**: `epic | task`
- **Target ID**: `<E-number-or-T-number>`
- **Domain**: `<required-domain>`
- **Module**: `<required-module>`
- **Prepared Date**: `YYYY-MM-DD`
- **Validated Date**: `YYYY-MM-DD`

## Required Context

| Đường dẫn | Mục đích | Thẩm quyền | Bắt buộc |
|---|---|---|---|
| `<repository-relative-path>` | `<specific-use>` | `source | contract | governance | report | reference` | `yes | no` |

## Related Files

- **Current Context**: `.agent/execution/current-context.md`
- **Epic or Task Record**: `<path-and-anchor>`
- **Decisions**: `<paths-or-none>`
- **Risks**: `<paths-or-none>`
- **Blockers**: `<paths-or-none>`
- **Change Requests**: `<paths-or-none>`

## Governing Constraints

- **Required Approvals**: `<approval-record-paths-or-none>`
- **Security Constraints**: `<specific-constraints-or-none>`
- **Data Constraints**: `<specific-constraints-or-none>`
- **Forbidden Operations**: `<specific-operations-or-none>`

## Current State

- **Implemented State**: `<verified-summary>`
- **Known Gaps**: `<specific-gaps-or-none>`
- **Active Dependencies**: `<ids-or-none>`
- **Active Blockers**: `<ids-or-none>`

## Expected Outputs

| Output | Đường dẫn bắt buộc | Cách kiểm chứng |
|---|---|---|
| `<artifact-name>` | `<repository-relative-path>` | `<check-or-evidence>` |

## Completion Criteria

- [ ] Mọi đường dẫn bắt buộc đều tồn tại và đọc được.
- [ ] Thẩm quyền và mục đích nội dung được ghi cho từng đường dẫn.
- [ ] Ràng buộc và trạng thái hiện tại đã được kiểm tra vào ngày đã ghi.
- [ ] Output mong đợi ánh xạ tới bằng chứng kiểm chứng rõ ràng.

## Forbidden Actions

- Không đưa vào secret, credential, dữ liệu cá nhân hay nội dung repo không liên quan.
- Không đánh dấu `ready` khi còn thiếu ngữ cảnh bắt buộc.
- Không dùng package `stale` hoặc `archived` để thực thi.
- Không dùng bản tóm tắt thay cho contract hay governance record bắt buộc.

## Output Requirements

- Lưu package hoàn chỉnh tại đường dẫn đã được task hoặc epic duyệt trong `.agent/execution/`.
- Chỉ dùng đường dẫn tương đối theo repo.
- Giữ nguyên mọi heading và cột bảng trong template này.
