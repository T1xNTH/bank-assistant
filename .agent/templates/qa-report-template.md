---
id: qa-report-template
title: QA Report Template
type: report
domain: testing
module: templates
tags: [qa, testing, report, template]
priority: 3
---
# Template QA Report

## Usage Purpose

Dùng template này để ghi lại các kiểm tra, kết quả, lỗi và khuyến nghị hoàn thành của QA Agent sau khi review độc lập đã duyệt.

## Record Metadata

- **Report ID**: `TASK-ID`
- **Title**: `<required>`
- **Owner**: `<required-person-or-agent-id>`
- **Tester**: `<required-person-or-agent-id>`
- **Status**: `draft | passed | failed | blocked | superseded`
- **Task ID**: `TASK-ID`
- **Review Decision**: `APPROVED`
- **Test Date**: `YYYY-MM-DD`
- **Environment ID**: `<environment-name-or-id>`

## Test Scope

- **Features or Requirements**: `<ids-or-descriptions>`
- **Included Test Levels**: `unit | integration | contract | end-to-end | security | performance | manual`
- **Behavior Checks**: `<checks-or-none>`
- **Edge Cases**: `<checks-or-none>`
- **Regression Checklist**: `<path-or-inline-checklist>`
- **Excluded Checks**: `<checks-and-reasons-or-none>`

## Related Files

- **Test Plan or Strategy**: `<paths>`
- **Implementation Report**: `.agent/reports/implementation/TASK-ID.md`
- **Review Report**: `.agent/reports/review/TASK-ID.md`
- **Task Board**: `.agent/execution/task-board.md`
- **Current Context**: `.agent/execution/current-context.md`
- **Issues or Risks**: `<paths-or-none>`
- **Build or Commit**: `<identifier>`

## Command Evidence

| Lệnh | Kết quả | Bằng chứng |
|---|---|---|
| `agent qa start TASK-ID` | `passed | failed | not-run` | `<output-or-path>` |
| `agent qa pass TASK-ID` | `passed | failed | not-run` | `<output-or-path>` |
| `agent qa fail TASK-ID` | `passed | failed | not-run` | `<output-or-path>` |

## Test Results

| Check ID | Cấp test | Kết quả | Bằng chứng | Defect ID |
|---|---|---|---|---|
| `CHECK-<number>` | `<enum-value>` | `passed | failed | blocked | skipped` | `<path-or-output>` | `<issue-id-or-none>` |

## Result Summary

- **Total**: `<integer>`
- **Passed**: `<integer>`
- **Failed**: `<integer>`
- **Blocked**: `<integer>`
- **Skipped**: `<integer>`

## Defects and Risks

- **Open Defects**: `<issue-ids-or-none>`
- **Residual Risks**: `<risk-ids-or-none>`
- **Blocking Conditions**: `<blocker-ids-or-none>`

## Acceptance Criteria

- [ ] Review report ghi `APPROVED` trước khi QA bắt đầu.
- [ ] Mọi kiểm tra bắt buộc đều có kết quả và bằng chứng.
- [ ] Tổng số kết quả khớp với bảng kết quả.
- [ ] Kiểm tra fail đều ánh xạ tới issue record.
- [ ] Kiểm tra bị skip có lý do rõ ràng đã được duyệt.
- [ ] Hành vi, edge case, checklist regression và kiểm tra thủ công được ghi lại khi có.

## Release Recommendation

- **Recommendation**: `go | conditional-go | no-go`
- **Conditions**: `<required-for-conditional-go-or-none>`
- **Rationale**: `<required>`
- **Authorized By**: `<person-or-role-id>`

## Completion Criteria

- [ ] Các test bắt buộc đã chạy hoặc được miễn chính thức.
- [ ] Lỗi, blocker và rủi ro còn lại đã được liên kết.
- [ ] Khuyến nghị release khớp với kết quả đã ghi.

## Forbidden Actions

- Không bắt đầu QA trước khi review độc lập là `APPROVED`.
- Không đánh dấu `passed` khi còn lỗi bắt buộc chưa xử lý.
- Không bỏ sót, đổi nhãn hay loại bỏ kết quả fail.
- Không tính kiểm tra chưa chạy là passed.
- Không dùng QA thay cho review độc lập.
- Không đổi roadmap hay acceptance criteria.
- Không để lộ secret hay dữ liệu cá nhân production trong bằng chứng.

## Output Requirements

- Lưu thành `.agent/reports/qa/TASK-ID.md`.
- Giữ nguyên mọi heading và cột bảng trong template này.
- Dùng đúng giá trị enum và tổng số là số nguyên không âm.
