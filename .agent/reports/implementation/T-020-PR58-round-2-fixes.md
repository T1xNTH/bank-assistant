---
id: impl-t020-pr58-round2-fixes
title: T-020 PR58 second re-review corrections
type: report
domain: security
module: pii
tags: [implementation, t-020, pr58, round2]
priority: 1
---
# T-020 PR58 second re-review corrections

## Usage Purpose

Dùng template này để cung cấp bằng chứng có thể kiểm toán về công việc Executor Agent đã làm cho một task đã được phép.

## Record Metadata

- **Report ID**: `T-020-PR58-round-2-fixes`
- **Title**: `PR58 re-review attached accounts, phone suffixes and label fillers`
- **Owner**: `teammate-b`
- **Executor**: `codex-b`
- **Status**: `complete`
- **Task ID**: `T-020`
- **Epic ID**: `E-007`
- **Report Date**: `2026-10-30`

## Scope

- **Implemented**: `All four items from external Claude re-review at 28326eb: attached STK/TK account labels, letter suffixes after phones, bounded account label fillers, archive EOF cleanup; new regressions and docs.`
- **Not Implemented**: `Unbounded natural-language label parsing; new external approval, PR merge or task closure.`

## Changes Made

| File ho?c s?n ph?m | T?m t?t thay ??i | Task ID |
|---|---|---|
| `src/app/security/pii.py` | Attached STK/TK lookbehind, digit-only phone suffix boundary, bounded account filler phrases | `T-020` |
| `tests/security/test_pii.py` | 13 new failing-before/passing-after regressions; attached-label short/long/embedded negatives; idempotence | `T-020` |
| `tests/security/test_audit.py` | Verify attached account and suffixed phone are masked in HTTP 500 audit/log/response | `T-020` |
| `docs/06-security/security-design.md` | Describe intentional suffix over-masking, attached STK/TK and bounded fillers | `T-020` |
| `.agent/reports/review/T-020-claude-pr58.md` | Requested removal of blank EOF only; prior substantive content preserved | `T-020` |
| `.agent/reports/review/T-020-claude-pr58-round-2.md` | Attribute and archive external second re-review without claiming approval | `T-020` |

## Related Files

- **Task Records**: `.agent/execution/tasks/T-020.md; PR58 comment 6516910648`
- **Context Packages**: `AGENT.md; T-020; .agent/reports/review/T-020-claude-pr58-round-2.md; previous PR58 implementation/review reports`
- **Task Board**: `.agent/execution/task-board.md`
- **Current Context**: `.agent/execution/current-context.md`
- **Decisions**: `.agent/governance/decisions/DEC-001.md; .agent/governance/decisions/DEC-004.md`
- **Change Requests**: `none; correction of supported entity recognition within T-020 scope, no API/contract change`
- **Risks or Blockers**: `none for local Linux verification; latest head still needs external reviewer and peer approval`
- **Review Request**: `codex-review-a independent technical follow-up; caitoithap separate-Claude re-review and peer approval pending`
- **Commits**: `58db49e (source, tests, docs and explicitly requested EOF correction)`

## Command Evidence

| L?nh | K?t qu? | B?ng ch?ng |
|---|---|---|
| `git pull --ff-only origin feat/T-020-vn-pii` | `passed` | Already up to date at 28326eb before fixes |
| `gh api repos/caitoithap/bank-assistant/issues/comments/6516910648` | `passed` | Separate-Claude source re-review archived with decision/head attribution |
| `git commit source/tests/docs` | `passed` | 58db49e |

## Verification Evidence

| Ki?m tra | K?t qu? | B?ng ch?ng |
|---|---|---|
| `Pre-fix new re-review regressions, Python 3.10.22` | `failed` | All 13 regressions failed against 28326eb source |
| `Python 3.10.22 pytest tests/security/test_pii.py -q` | `passed` | 106 passed in 3.41s, Presidio2.2.365 |
| `WSL Python3.12 make check` | `passed` | 469 passed, 24 deselected in 118.38s; Ruff pass; FRAMEWORK_VALIDATION_PASS |
| `git diff origin/main --check` | `passed` | Whole PR whitespace check clean after requested EOF normalization |
| `Original archive comparison with git show 28326eb` | `passed` | old.rstrip() equals new.rstrip(); exactly one trailing newline, no substantive review changes |

## Deviations

- **Plan Deviations**: `No scope or contract expansion. Replace the old negative phone-letter case with intentional privacy-first masking; account arbitrary-word prefixes remain excluded unless the attached label is STK/TK. Only trailing blank whitespace is modified in the earlier archived review, per explicit reviewer request.`
- **Approved By**: `not-applicable; existing user request and reviewer bounded correction requests, no baseline scope or contract change`
- **Known Limitations**: `Account fillers support one phrase s?/so or c?a t?i l?/cua toi la; arbitrary fillers are not parsed. Existing bare grouped phone-prefix ambiguity and full-width-digit exclusions remain documented. Second external re-review is CHANGES_REQUESTED at 28326eb; new code still requires external re-review/peer approval.`

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
