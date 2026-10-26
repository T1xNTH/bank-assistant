---
id: agent-cli
title: Agent Lifecycle CLI
type: reference
domain: development
module: tooling
tags: [agent, cli, lifecycle, tooling]
priority: 2
---
# Agent Lifecycle CLI

## Mục đích

`scripts/agent` hiện thực bộ lệnh `agent task|review|qa|epic` mà prompt pack ở `docs/10-agents/` nhắc tới. Lệnh chỉ dùng Python stdlib. Mọi trạng thái tuân theo enum trong `AGENT.md` (decision DEC-002):
- task: `pending | in-progress | blocked | review | done | cancelled`
- epic: `EPIC_PROPOSED | EPIC_READY | EPIC_IN_PROGRESS | EPIC_BLOCKED | EPIC_DONE | EPIC_CANCELLED`

Ánh xạ với workflow trong prompt pack:
- `IMPLEMENTED/REVIEWING` → `review`
- `CHANGES_REQUESTED` → quay lại `in-progress`
- `APPROVED/DONE` → `done`

## Các lệnh

| Lệnh | Điều kiện kiểm tra | Kết quả |
|---|---|---|
| `agent epic status E-xxx EPIC_READY` | epic có owner (không phải `unassigned`) | đổi trạng thái epic |
| `agent epic status E-xxx EPIC_IN_PROGRESS` | từ READY: có ≥ 1 task; từ BLOCKED: mọi blocker đã `resolved/accepted/cancelled` | |
| `agent epic status E-xxx EPIC_BLOCKED --blocker BLOCKER-xxx` | file blocker tồn tại | blocker được thêm vào Governance Links |
| `agent epic status E-xxx EPIC_DONE` | mọi task `done/cancelled` và `.agent/reports/qa/E-xxx.md` có Status `passed` | |
| `agent epic status E-xxx EPIC_CANCELLED --change-request CR-xxx` | CR đã `approved` | |
| `agent task add T-xxx --epic E-xxx --title … --owner … [--deps T-a,T-b]` | epic đang `EPIC_READY`, deps đã có trên board | thêm dòng `pending` và thêm id vào Task IDs của epic |
| `agent task start T-xxx` | epic `EPIC_IN_PROGRESS`, có owner, deps `done`, blocker (nếu có) đã giải quyết | `in-progress` |
| `agent task block T-xxx --blocker BLOCKER-xxx` | task `in-progress`, file blocker tồn tại | `blocked` |
| `agent task report T-xxx --executor <id> [--complete]` | task `in-progress`; `--complete` cần ít nhất một dòng verify `passed` | tạo hoặc cập nhật implementation report |
| `agent task verify T-xxx [--cmd "make check"]` | task `in-progress` | chạy lệnh và ghi một dòng vào Verification Evidence; thoát với mã 1 nếu lệnh fail |
| `agent review request T-xxx --reviewer <id>` | report `complete`, reviewer ≠ executor | `review` |
| `agent review start T-xxx --reviewer <id>` | task `review`, reviewer ≠ executor | review report `draft` |
| `agent review approve T-xxx --reviewer <id>` | như trên | review `approved` |
| `agent review request-changes T-xxx --reviewer <id>` | như trên | review `changes-required`, task về `in-progress`, impl report về `draft` |
| `agent task done T-xxx` | task `review` + review report `approved` | `done` |
| `agent task cancel T-xxx --reason …` | task chưa ở trạng thái kết thúc | `cancelled` |
| `agent qa start E-xxx --qa <id>` | epic `EPIC_IN_PROGRESS`, mọi task `done/cancelled` | QA report theo epic, `draft` (DEC-005) |
| `agent qa pass/fail E-xxx --qa <id>` | QA report đang `draft` | `passed`/`failed` |
| `agent status` | — | in task board nhóm theo epic |

Tuỳ chọn chung: `agent --actor <id> …` ghi danh tính vào session history. Mặc định dùng owner của bản ghi.

## Hành vi

- **Lỗi quy tắc:** in `agent: error: …` và thoát với mã `2`. Khi đó **không file nào bị ghi**: mọi thay đổi được gom lại rồi ghi bằng temp file + `os.replace`.
- **Bảng:** mỗi lệnh chỉ sửa đúng dòng của bản ghi đích, phần còn lại của file giữ nguyên. Mọi ô được bọc trong backtick. Giá trị không được chứa `|`, backtick hay xuống dòng.
- **Session history:** mỗi lệnh thay đổi trạng thái sẽ cập nhật `Updated Date` và append một dòng vào `.agent/execution/sessions-history.md`. Session ID có dạng `S-YYYYMMDD-HHMMSS`, Outcome là `completed`.
- **Report:** sinh từ `.agent/templates/`. Placeholder `<…>` được thay bằng `TBD`, vì validator không chấp nhận `<required…>` trong runtime record. Executor/reviewer/QA tự điền phần nội dung `TBD` trước khi đánh dấu complete hay approved.
- **Thư mục gốc repo:** lấy theo `git rev-parse --show-toplevel`, hoặc biến `AGENT_ROOT` (test dùng cách này).

## Luồng điển hình

```bash
scripts/agent epic status E-003 EPIC_READY
scripts/agent task add T-010 --epic E-003 --title "docling parser" --owner trong-hung
scripts/agent epic status E-003 EPIC_IN_PROGRESS
scripts/agent task start T-010
scripts/agent task report T-010 --executor claude-code-a
scripts/agent task verify T-010 --cmd "make check"
scripts/agent task report T-010 --executor claude-code-a --complete
scripts/agent review request T-010 --reviewer claude-review-b
scripts/agent review start T-010 --reviewer claude-review-b
scripts/agent review approve T-010 --reviewer claude-review-b
scripts/agent task done T-010
scripts/agent qa start E-003 --qa qa-a && scripts/agent qa pass E-003 --qa qa-a
scripts/agent epic status E-003 EPIC_DONE
```

## Test

`python3 -m unittest discover -s tests/framework`, hoặc `pytest tests/framework`. Test chạy trên một bản copy tạm của repo, có test cho từng quy tắc chuyển trạng thái. Có một luồng đầy đủ đi hết lifecycle rồi kiểm tra `scripts/validate-framework.py` không phát sinh lỗi mới.
