---
id: impl-T-026-pr88-fixes
title: Implementation Report T-026 PR88 fixes
type: report
domain: governance
module: execution
tags: [implementation, report, T-026, pr-88]
priority: 2
---
# Implementation Report T-026 PR88 fixes

## Usage Purpose

Bằng chứng cho phần sửa theo review của B trên PR #88. Report này bổ sung `.agent/reports/implementation/T-026.md` và không thay thế report đó.

## Record Metadata

- **Report ID**: `T-026-PR88-fixes`
- **Title**: `Worker route local cho payload cũ có PII`
- **Owner**: `trong-hung`
- **Executor**: `claude (Claude Code, Opus 5.5, session "nhân viên 4")`
- **Status**: `complete`
- **Task ID**: `T-026`
- **Epic ID**: `E-010`
- **Report Date**: `2026-11-02`

## Scope

- **Implemented**: `PR88 P2: job enqueue trước T-026 có force_local=false cạnh câu hỏi đã che. Worker che lại câu hỏi bằng require_mask. Nếu có PII còn sót hoặc có placeholder <CCCD>/<ACCOUNT_NUMBER>/<PHONE_NUMBER> (masking.masked_pii_types) thì đặt force_local=true (fail-closed). Không cần migration và không đổi schema payload.`
- **Not Implemented**: `none`

## Changes Made

| File hoặc sản phẩm | Tóm tắt thay đổi | Task ID |
|---|---|---|
| `src/app/security/masking.py` | `masked_pii_types(text): loại PII theo placeholder trong văn bản đã che` | `T-026` |
| `src/app/queue/jobs.py` | `execute_ask: force_local = payload.force_local OR PII sót OR placeholder; che một lần trước run_with_policy` | `T-026` |
| `tests/api/test_ask_routing.py` | `5 test payload kiểu cũ: 3 placeholder -> local, PII chưa che -> local và LLM chỉ nhận văn bản đã che, không PII -> cloud` | `T-026` |

## Related Files

- **Task Records**: `.agent/execution/tasks/T-026.md`
- **Context Packages**: `PR #88 review comment của B tại a88c188`
- **Task Board**: `.agent/execution/task-board.md`
- **Current Context**: `.agent/execution/current-context.md`
- **Decisions**: `DEC-001`
- **Change Requests**: `CR-003 (C-1). Placeholder chỉ là tín hiệu bổ sung, fail-closed; tín hiệu chính vẫn là PII phát hiện lúc enqueue, đúng ý "không dò lại chỉ trên câu hỏi đã che".`
- **Risks or Blockers**: `none`
- **Review Request**: `pending — re-review của B và claude-review-a`
- **Commits**: `e821c94`

## Command Evidence

| Lệnh | Kết quả | Bằng chứng |
|---|---|---|
| `pytest tests/api/test_ask_routing.py` (trước khi sửa) | `failed` | `4 failed, 14 passed: payload cũ route cloud (RED)` |
| `pytest tests/unit/test_routing.py tests/api/test_ask_routing.py` | `passed` | `37 passed in 5.69s` |
| `make check` | `passed` | `802 passed, 50 deselected in 32.98s; FRAMEWORK_VALIDATION_PASS` |

## Verification Evidence

| Kiểm tra | Kết quả | Bằng chứng |
|---|---|---|
| `pytest -m integration tests/integration/test_worker.py` | `passed` | `5 passed in 16.61s (Redis/worker thật)` |

## Deviations

- **Plan Deviations**: `none`
- **Approved By**: `none needed (sửa trong phạm vi T-026)`
- **Known Limitations**: `Câu hỏi người dùng tự gõ chuỗi "<CCCD>" sẽ route local; chấp nhận vì nghiêng về an toàn.`

## Completion Criteria

- [x] Mọi thay đổi được báo cáo đều ánh xạ tới một task đã được phép.
- [x] Kết quả và bằng chứng của acceptance criteria đã được liên kết.
- [x] Sai lệch và giới hạn được nêu rõ.
- [x] Kiểm tra build, lint, test đã được ghi lại hoặc đánh dấu rõ not-run kèm lý do.
- [x] Phần bàn giao cho reviewer nêu rõ một Reviewer Agent độc lập.
- [x] Ánh xạ Git Nexus được cập nhật khi đã có commit.

## Forbidden Actions

- Không báo cáo việc chưa làm là đã hiện thực.
- Không bỏ sót kiểm tra bắt buộc bị fail hoặc chưa chạy.
- Không tuyên bố hoàn thành khi acceptance criteria của task chưa đạt.
- Không tuyên bố review đã duyệt hay chuyển task sang `DONE`.
- Không đổi roadmap hay acceptance criteria.
- Không dùng report này thay cho review độc lập.
- Không đưa secret hay output lệnh nhạy cảm vào.

## Output Requirements

- Lưu thành `.agent/reports/implementation/T-026-PR88-fixes.md`.
- Giữ nguyên mọi heading và cột bảng trong template này.
- Chỉ đặt trạng thái `complete` sau khi các completion criteria đều đạt.
