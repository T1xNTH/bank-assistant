---
id: review-report-template
title: Review Report Template
type: report
domain: quality
module: templates
tags: [review, report, template]
priority: 3
---
# Template Review Report

## Usage Purpose

Dùng template này để ghi lại đánh giá của một Reviewer Agent độc lập về phần hiện thực của Executor Agent.

## Record Metadata

- **Report ID**: `TASK-ID`
- **Title**: `<required>`
- **Owner**: `<required-person-or-agent-id>`
- **Reviewer**: `<required-person-or-agent-id>`
- **Executor**: `<executor-id>`
- **Status**: `draft | changes-requested | approved | blocked | superseded`
- **Decision**: `APPROVED | CHANGES_REQUESTED | BLOCKED`
- **Review Type**: `code | architecture | documentation | security | performance | governance | release`
- **Task ID**: `TASK-ID`
- **Report Date**: `YYYY-MM-DD`

## Review Scope

- **Included Artifacts**: `<paths-or-commit-range>`
- **Code Diff**: `<path-or-commit-range>`
- **Excluded Artifacts**: `<paths-or-none>`
- **Review Standard**: `<criteria-checklist-or-policy-path>`

## Related Files

- **Implementation Report**: `.agent/reports/implementation/TASK-ID.md`
- **Task or Epic Records**: `<paths-and-anchors>`
- **Task Board**: `.agent/execution/task-board.md`
- **Current Context**: `.agent/execution/current-context.md`
- **Decisions**: `<paths-or-none>`
- **Risks or Issues**: `<paths-or-none>`
- **Verification Evidence**: `<paths-or-none>`

## Command Evidence

| Lệnh | Kết quả | Bằng chứng |
|---|---|---|
| `agent review start TASK-ID` | `passed | failed | not-run` | `<output-or-path>` |
| `agent review approve TASK-ID` | `passed | failed | not-run` | `<output-or-path>` |
| `agent review request-changes TASK-ID` | `passed | failed | not-run` | `<output-or-path>` |
| `agent review block TASK-ID` | `passed | failed | not-run` | `<output-or-path>` |

## Required Review Checks

| Kiểm tra | Kết quả | Bằng chứng |
|---|---|---|
| Code diff | `passed | failed | blocked | not-run` | `<evidence>` |
| Acceptance criteria | `passed | failed | blocked | not-run` | `<evidence>` |
| Tuân thủ kiến trúc | `passed | failed | blocked | not-run` | `<evidence>` |
| Bảo mật | `passed | failed | blocked | not-run` | `<evidence>` |
| Hiệu năng | `passed | failed | blocked | not-run` | `<evidence>` |
| Rủi ro regression | `passed | failed | blocked | not-run` | `<evidence>` |
| Bằng chứng test/lint/build | `passed | failed | blocked | not-run` | `<evidence>` |

## Findings

| Finding ID | Mức độ | Sản phẩm | Finding | Hành động cần làm | Owner |
|---|---|---|---|---|---|
| `F-<number>` | `critical | major | minor | observation` | `<path>` | `<specific-finding>` | `<action-or-none>` | `<person-or-agent-id>` |

## Acceptance Criteria

- [ ] Phạm vi và chuẩn review được nêu rõ.
- [ ] Mỗi finding nêu bằng chứng, mức độ, hành động và owner.
- [ ] Finding critical và major đã được giải quyết hoặc chấp nhận chính thức.
- [ ] Kết quả duyệt khớp với các finding chưa giải quyết.
- [ ] Đã kiểm tra code diff, acceptance criteria, kiến trúc, bảo mật, hiệu năng, rủi ro regression và bằng chứng test/lint/build.
- [ ] Danh tính reviewer độc lập với danh tính executor.

## Approval Outcome

- **Decision**: `APPROVED | CHANGES_REQUESTED | BLOCKED`
- **Rationale**: `<required>`
- **Approved By**: `<reviewer-or-authorized-role>`
- **Decision Date**: `YYYY-MM-DD`
- **Follow-up Tasks**: `<task-ids-or-none>`

## Completion Criteria

- [ ] Mọi hành động bắt buộc đã được liên kết với task hoặc đã kiểm chứng là đã giải quyết.
- [ ] Kết quả duyệt và lý do đã được ghi lại.
- [ ] Các record issue, risk và report liên quan đã được cập nhật.

## Forbidden Actions

- Không duyệt sản phẩm khi còn finding critical chưa giải quyết.
- Không xoá finding sau khi đã sửa; hãy ghi lại cách giải quyết.
- Không gán mức độ hay owner mơ hồ.
- Không tuyên bố đã review những phần nằm ngoài phạm vi đã khai báo.
- Không đóng vai Executor Agent cho cùng task.
- Không chuyển task sang `DONE`; QA phải chạy sau `APPROVED`.
- Không đổi roadmap hay acceptance criteria.

## Output Requirements

- Lưu thành `.agent/reports/review/TASK-ID.md`.
- Giữ nguyên mọi heading và cột bảng trong template này.
- Dùng link tương đối theo repo và đúng giá trị enum.
