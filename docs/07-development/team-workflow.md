---
id: team-workflow
title: Team Workflow (2 người)
type: reference
domain: development
module: repository
tags: [workflow, git, review, sdlc]
priority: 1
---
# Team Workflow (2 người)

## Vai trò
| Người | ID | Mảng | Vai trò kit |
|---|---|---|---|
| A — trong-hung | `trong-hung` | AI/dữ liệu: `src/app/rag/`, `prompts.py`, `routing.py`, `agent/graph.py` + tools, `eval/`, `ui/` | coordinator, governance (roadmap), executor cho task của mình |
| B — bạn đồng đội | `teammate-b` | Nền tảng: `main.py`, `schemas.py`, `llm.py`, `security/`, `queue/`, `tracing.py`, `infrastructure/`, CI | executor cho task của mình, governance đồng duyệt contract/SRS |

Reviewer của mỗi task = **một phiên Claude Code mới** (không phải phiên đã code) + người còn lại duyệt PR (DEC-004).

## Vòng đời một task (lệnh `scripts/agent`, xem `agent-cli.md`)
```bash
scripts/agent task start T-012
git switch -c feat/T-012-hybrid-rrf
# … Claude Code (executor) code theo TDD …
scripts/agent task report T-012 --executor claude-code-A
scripts/agent task verify T-012            # chạy make check, ghi evidence
scripts/agent task report T-012 --executor claude-code-A --complete
scripts/agent review request T-012 --reviewer claude-review-A
# mở phiên Claude Code MỚI: "Đọc docs/10-agents/reviewer-prompt.md, review T-012"
scripts/agent review start T-012 --reviewer claude-review-A
scripts/agent review approve T-012 --reviewer claude-review-A   # hoặc request-changes
# mở PR → người kia duyệt → squash merge
scripts/agent task done T-012
```
Khi mọi task của epic xong: `scripts/agent qa start E-004 --qa <id>` → chạy QA → `qa pass` → `epic status E-004 EPIC_DONE`.

## Git
- `main` được bảo vệ: cần 1 review + CI xanh, merge kiểu squash.
- Nhánh `feat|fix|docs/T-xxx-<mô-tả>`; Conventional Commits; PR < 400 dòng.
- Mỗi PR chỉ sửa **dòng task của chính mình** trong `task-board.md`; `sessions-history.md` chỉ append (conflict thì giữ cả hai dòng).
- `current-context.md` chỉ coordinator (A) sửa, mỗi sáng.
- Đổi `docs/04-api/openapi.yaml` hoặc `src/app/contracts.py` → PR riêng, label `contract`, cả hai duyệt + change request.

## Definition of Done (task)
- [ ] Acceptance criteria của task đạt, có lệnh verify.
- [ ] `make check` xanh (ruff, pytest, framework validation), output sạch.
- [ ] Implementation report `complete` + review report `approved`.
- [ ] Không secret/PII trong code, log, fixture.
- [ ] Docs/OpenAPI cập nhật nếu đổi hành vi; từ E-008: eval không tụt dưới `eval/thresholds.json`.

## Nhịp
- 10 phút sync đầu ngày (hôm qua / hôm nay / vướng) → A cập nhật `current-context.md`.
- Merge `main` ≥ 1 lần/ngày; smoke test cuối ngày (`make check`, sau N2 thêm `make up` + `curl /health`).
- Cuối N1: tách task cho epic của M-001. Cuối N5: release v0.1, retro, tách task cho M-002. Cuối N10: release v1.0-mvp.
- Hết token limit giữa chừng: commit WIP lên nhánh, ghi trạng thái vào implementation report, người kia có thể tiếp tục.
