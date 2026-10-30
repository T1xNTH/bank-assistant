---
id: impl-t020-pr58-round3-fixes
title: T-020 PR58 attached CCCD correction
type: report
domain: security
module: pii
tags: [implementation, t-020, pr58, round3]
priority: 1
---
# T-020 PR58 attached CCCD correction

## Usage Purpose

Dùng template này để cung cấp bằng chứng có thể kiểm toán về công việc Executor Agent đã làm cho một task đã được phép.

## Record Metadata

- **Report ID**: `T-020-PR58-round-3-fixes`
- **Title**: `Support CCCD labels attached to identity numbers`
- **Owner**: `teammate-b`
- **Executor**: `codex-b`
- **Status**: `complete`
- **Task ID**: `T-020`
- **Epic ID**: `E-007`
- **Report Date**: `2026-10-30`

## Scope

- **Implemented**: `User-requested optional suggestion from external no-blockers review at c4392ea: attached CCCD labels (case-insensitive), including grouped identity digits; public masking/idempotence regressions, negative boundary/length checks, audit failure-path regression and docs.`
- **Not Implemented**: `New-head approval, PR merge or task closure; unrelated format expansion.`

## Changes Made

| File ho?c s?n ph?m | T?m t?t thay ??i | Task ID |
|---|---|---|
| `src/app/security/pii.py` | Permit a word-boundary CCCD label directly before 12 identity digits | `T-020` |
| `tests/security/test_pii.py` | Six attached-label/case/grouped cases plus three negative embedded/short/long cases | `T-020` |
| `tests/security/test_audit.py` | Assert attached CCCD is masked in audit/response/log on answerer failure | `T-020` |
| `docs/06-security/security-design.md` | Add CCCD to documented attached numeric labels | `T-020` |
| `.agent/reports/review/T-020-claude-pr58-round-3.md` | Archive external technical no-blockers assessment at c4392ea with exact provenance | `T-020` |

## Related Files

- **Task Records**: `.agent/execution/tasks/T-020.md; PR58 comment 6517216112`
- **Context Packages**: `AGENT.md; T-020; .agent/reports/review/T-020-claude-pr58-round-3.md; prior immutable PR58 evidence`
- **Task Board**: `.agent/execution/task-board.md`
- **Current Context**: `.agent/execution/current-context.md`
- **Decisions**: `.agent/governance/decisions/DEC-001.md; .agent/governance/decisions/DEC-004.md`
- **Change Requests**: `none; correction of supported entity recognition within T-020 scope, no API/contract change`
- **Risks or Blockers**: `none in local Linux verification; optional new-head correction remains for reviewer verification`
- **Review Request**: `caitoithap (separate Claude reviewer) to verify optional attached-CCCD correction; peer PR approval remains separate`
- **Commits**: `dbdb0aa (source, tests and docs)`

## Command Evidence

| L?nh | K?t qu? | B?ng ch?ng |
|---|---|---|
| `git pull --ff-only origin feat/T-020-vn-pii` | `passed` | Up to date at c4392ea before correction |
| `gh api repos/caitoithap/bank-assistant/issues/comments/6517216112` | `passed` | External no-blockers review and optional suggestion archived, attribution preserved |
| `git commit source/tests/docs` | `passed` | dbdb0aa |

## Verification Evidence

| Ki?m tra | K?t qu? | B?ng ch?ng |
|---|---|---|
| `Pre-fix attached-CCCD regressions, Python 3.10.22` | `failed` | Six positive attached-label cases fail against c4392ea |
| `Python 3.10.22 pytest tests/security/test_pii.py -q` | `passed` | 115 passed in 2.49s; Presidio2.2.365 |
| `WSL Python3.12 make check` | `passed` | 479 passed, 24 deselected in 102.80s; Ruff passed; FRAMEWORK_VALIDATION_PASS |
| `git diff origin/main --check` | `passed` | No whole-PR whitespace errors |

## Deviations

- **Plan Deviations**: `none; apply the same bounded attached-label exception used for STK/TK to CCCD. Do not relax arbitrary-word prefixes or identity length/right boundary checks.`
- **Approved By**: `not-applicable; existing user request and reviewer bounded correction requests, no baseline scope or contract change`
- **Known Limitations**: `Existing unsupported formats, full-width-digit exclusion and documented bare phone-prefix ambiguity remain unchanged. External no-blockers assessment applies to c4392ea only; it is not approval of subsequent code or a submitted GitHub approval.`

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

- Lưu thành `.agent/reports/implementation/TASK-ID.md`.
- Giữ nguyên mọi heading và cột bảng trong template này.
- Chỉ đặt trạng thái `complete` sau khi các completion criteria đều đạt.
