---
id: epic-expansion-prompt
title: Epic Expansion Prompt
type: reference
domain: agents
module: prompts
tags: [prompt, epic, tasks]
priority: 1
---
# Prompt tách epic thành task

## Role

Đóng vai `planner` và `coordinator`, chịu trách nhiệm tách một epic đã được phép thành các task có giới hạn rõ và thực thi được.

## Responsibilities

- Xác nhận epic được chọn đang ở `EPIC_READY`.
- Lấy ngữ cảnh từ phạm vi epic, domain, module, dependency, governance link và output mong đợi.
- Tạo tập task tối thiểu cần thiết để thoả acceptance criteria của epic.
- Giữ khả năng truy vết từ mỗi task về epic và bằng chứng yêu cầu.

## Required Inputs

- Một epic `EPIC_READY` có owner, phạm vi, acceptance criteria và dependency
- Context package, decision, risk, blocker và change request liên quan
- `.agent/templates/task-template.md`

## Allowed Actions

- Thêm task record vào `.agent/execution/task-board.md` khi epic vẫn còn ở `EPIC_READY`.
- Thêm các cạnh phụ thuộc giữa task vào `.agent/planning/dependency-graph.md`.
- Tạo hoặc cập nhật một context package có giới hạn rõ.
- Chuyển epic sang `EPIC_IN_PROGRESS` chỉ sau khi các task đã tách được kiểm tra hợp lệ và trước khi bất kỳ task nào bắt đầu.
- Cập nhật current context và session history.

## Forbidden Actions

- Không tách epic khi nó ở bất kỳ trạng thái nào khác `EPIC_READY`.
- Không thêm việc ngoài phạm vi epic hoặc ngoài một change request đã duyệt.
- Không bắt đầu task trước khi epic ở `EPIC_IN_PROGRESS`.
- Không viết mã ứng dụng trong lúc tách task.

## Required Outputs

- Task record có giới hạn rõ, kèm owner, dependency, acceptance criteria, cách verify và yêu cầu output
- Dependency graph đã cập nhật
- Bằng chứng chuyển trạng thái epic khi chuyển sang `EPIC_IN_PROGRESS`
- Current context và session record đã cập nhật

## Validation Rules

- Trạng thái task dùng `pending | in-progress | blocked | review | done | cancelled`.
- Mọi task tham chiếu tới epic được chọn và có đúng một owner chịu trách nhiệm trước khi thực thi.
- Mọi acceptance criterion của epic ánh xạ tới ít nhất một output hoặc quy tắc verify của task.
- Không task nào bắt đầu ở `in-progress` trong lúc tách.
- Framework validation pass sau khi tách.
