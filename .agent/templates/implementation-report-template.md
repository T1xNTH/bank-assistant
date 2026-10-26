---
id: implementation-report-template
title: Implementation Report Template
type: report
domain: development
module: templates
tags: [implementation, report, template]
priority: 3
---
# Template Implementation Report

## Usage Purpose

Dùng template này để cung cấp bằng chứng có thể kiểm toán về công việc Executor Agent đã làm cho một task đã được phép.

## Record Metadata

- **Report ID**: `TASK-ID`
- **Title**: `<required>`
- **Owner**: `<required-person-or-agent-id>`
- **Executor**: `<executor-id>`
- **Status**: `draft | complete | blocked | superseded`
- **Task ID**: `TASK-ID`
- **Epic ID**: `E-<number>`
- **Report Date**: `YYYY-MM-DD`

## Scope

- **Implemented**: `<specific-deliverables>`
- **Not Implemented**: `<excluded-or-deferred-items-or-none>`

## Changes Made

| File hoặc sản phẩm | Tóm tắt thay đổi | Task ID |
|---|---|---|
| `<repository-relative-path>` | `<specific-change>` | `T-<number>` |

## Related Files

- **Task Records**: `<paths-and-anchors>`
- **Context Packages**: `<paths>`
- **Task Board**: `.agent/execution/task-board.md`
- **Current Context**: `.agent/execution/current-context.md`
- **Decisions**: `<paths-or-none>`
- **Change Requests**: `<paths-or-none>`
- **Risks or Blockers**: `<paths-or-none>`
- **Review Request**: `<reviewer-id-or-pending>`
- **Commits**: `<hashes-or-none-with-reason>`

## Command Evidence

| Lệnh | Kết quả | Bằng chứng |
|---|---|---|
| `agent task start TASK-ID` | `passed | failed | not-run` | `<output-or-path>` |
| `agent task verify TASK-ID` | `passed | failed | not-run` | `<output-or-path>` |
| `agent task report TASK-ID --executor <executor-id>` | `passed | failed | not-run` | `<output-or-path>` |
| `agent review request TASK-ID --reviewer <reviewer-id>` | `passed | failed | not-run` | `<output-or-path>` |

## Verification Evidence

| Kiểm tra | Kết quả | Bằng chứng |
|---|---|---|
| `<command-or-review>` | `passed | failed | not-run` | `<output-or-path>` |

## Deviations

- **Plan Deviations**: `<deviations-or-none>`
- **Approved By**: `<approval-path-or-not-applicable>`
- **Known Limitations**: `<limitations-or-none>`

## Completion Criteria

- [ ] Mọi thay đổi được báo cáo đều ánh xạ tới một task đã được phép.
- [ ] Kết quả và bằng chứng của acceptance criteria đã được liên kết.
- [ ] Sai lệch và giới hạn được nêu rõ.
- [ ] Kiểm tra build, lint, test đã được ghi lại hoặc đánh dấu rõ not-run kèm lý do.
- [ ] Phần bàn giao cho reviewer nêu rõ một Reviewer Agent độc lập.
- [ ] Ánh xạ Git Nexus được cập nhật khi đã có commit.

## Forbidden Actions

- Không báo cáo việc chưa làm là đã hiện thực.
- Không bỏ sót kiểm tra bắt buộc bị fail hoặc chưa chạy.
- Không tuyên bố hoàn thành khi acceptance criteria của task chưa đạt.
- Không tuyên bố review đã duyệt hay chuyển task sang `DONE`.
- Không đổi roadmap hay acceptance criteria.
- Không dùng report này thay cho review độc lập.
- Không đưa secret hay output lệnh nhạy cảm vào.

## Output Requirements

- Lưu thành `.agent/reports/implementation/TASK-ID.md`.
- Giữ nguyên mọi heading và cột bảng trong template này.
- Chỉ đặt trạng thái `complete` sau khi các completion criteria đều đạt.
