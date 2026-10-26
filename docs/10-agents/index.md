---
id: agents-overview
title: Agents
type: reference
domain: agents
module: repository
tags: [agents, coordination, tools]
priority: 2
---
# Agents

## Mục đích

Mục lục cho các prompt vai trò dùng lại được và tài liệu điều phối agent trong lifecycle của framework.

## Workflow agent chuẩn

Workflow task chuẩn là:

`Orchestrator -> Executor Agent -> Implementation Report -> Reviewer Agent -> QA Agent -> DONE`

Executor Agent và Reviewer Agent là hai vai trò tách biệt:

- `Executor Agent != Reviewer Agent`
- Codex Extension và Claude Code là adapter cho executor.
- Codex CLI và Claude CLI là adapter cho reviewer.

Các file bàn giao bắt buộc:

- Implementation report: `.agent/reports/implementation/TASK-ID.md`
- Review report: `.agent/reports/review/TASK-ID.md`
- QA report: `.agent/reports/qa/TASK-ID.md`
- Task board: `.agent/execution/task-board.md`
- Current context: `.agent/execution/current-context.md`

Lifecycle của task trong workflow này:

`BACKLOG -> READY -> IN_PROGRESS -> IMPLEMENTED -> REVIEWING -> APPROVED -> DONE`

Nếu reviewer yêu cầu sửa, task chuyển `CHANGES_REQUESTED -> IN_PROGRESS`. Nếu không thể tiếp tục, task chuyển sang `BLOCKED`.

Trong repo này, các trạng thái trên được ánh xạ sang enum của `AGENT.md` (DEC-002): `IMPLEMENTED/REVIEWING` → `review`, `CHANGES_REQUESTED` → `in-progress`, `APPROVED/DONE` → `done` (sau QA). Xem `docs/07-development/agent-cli.md`.

## Command contract

Luồng của executor:

```bash
agent task start TASK-ID
agent task verify TASK-ID
agent task report TASK-ID --executor <executor-id>
agent review request TASK-ID --reviewer <reviewer-id>
```

Luồng của reviewer:

```bash
agent review start TASK-ID
agent review approve TASK-ID
agent review request-changes TASK-ID
agent review block TASK-ID
```

Luồng của QA:

```bash
agent qa start TASK-ID
agent qa pass TASK-ID
agent qa fail TASK-ID
```

## Bộ prompt

- `project-bootstrap-prompt.md` - Kiểm tra hoặc khôi phục cấu trúc framework
- `project-onboarding-prompt.md` - Nạp input chính thức và tạo Planning Truth ban đầu
- `roadmap-lock-prompt.md` - Quản trị việc duyệt roadmap nháp
- `epic-expansion-prompt.md` - Tách một epic `EPIC_READY` thành các task
- `executor-prompt.md` - Thực thi một task đã được phép
- `reviewer-prompt.md` - Thực hiện review độc lập
- `qa-prompt.md` - Chạy QA và đưa ra khuyến nghị release
- `release-manager-prompt.md` - Kiểm tra và ghi lại việc thực hiện release

## Tài liệu liên quan

- `AGENT.md` - Quy định chính thức về vai trò agent, quyền hạn và lifecycle
- `.agent/templates/` - Template dùng lại cho governance, execution và report
