---
id: impl-t020-pr58-fixes
title: T-020 PR58 Claude review format corrections
type: report
domain: security
module: pii
tags: [implementation, t-020, pr58, review-fixes]
priority: 1
---
# T-020 PR58 Claude review format corrections

## Usage Purpose

Dùng template này để cung cấp bằng chứng có thể kiểm toán về công việc Executor Agent đã làm cho một task đã được phép.

## Record Metadata

- **Report ID**: `T-020-PR58-fixes`
- **Title**: `Resolve Claude PR58 grouped-number and phone-label comments`
- **Owner**: `teammate-b`
- **Executor**: `codex-b`
- **Status**: `complete`
- **Task ID**: `T-020`
- **Epic ID**: `E-007`
- **Report Date**: `2026-10-30`

## Scope

- **Implemented**: `PR58 review items 1-4: grouped ASCII CCCD/account formats, (+84), attached phone labels, public regressions; item 6: exact external Claude review archive; item 7: audit limits note. Pull coordinator 4bf3a17 before editing.`
- **Not Implemented**: `Full-width digit normalization (reviewer accepted exclusion); T-021 broader wiring; external re-review/peer approval; task closure.`

## Changes Made

| File hoặc sản phẩm | Tóm tắt thay đổi | Task ID |
|---|---|---|
| `src/app/security/pii.py` | Grouped numeric regex, parenthesized country, attached-phone boundary, labelled anchors and phone-delimited gaps | `T-020` |
| `tests/security/test_pii.py` | Review inputs, grouped boundaries, explicit numeric/phone ambiguity and preserved F01 regressions | `T-020` |
| `tests/security/test_audit.py` | Grouped CCCD/account and attached phone redaction on HTTP 500 with no raw PII in DB/response/log | `T-020` |
| `docs/06-security/security-design.md`, `docs/07-development/audit.md` | Supported forms, grouping ambiguity, intentional false positives and unsupported audit PII | `T-020` |
| `.agent/reports/review/T-020-claude-pr58.md` | Verbatim archive of external separate-Claude review; recorder is not the reviewer | `T-020` |

## Related Files

- **Task Records**: `.agent/execution/tasks/T-020.md; PR #58; source review comment 6515181908`
- **Context Packages**: `AGENT.md; T-020; .agent/reports/review/T-020-claude-pr58.md; existing F01 regression evidence`
- **Task Board**: `.agent/execution/task-board.md`
- **Current Context**: `.agent/execution/current-context.md`
- **Decisions**: `.agent/governance/decisions/DEC-001.md; .agent/governance/decisions/DEC-004.md`
- **Change Requests**: `none; correction of supported entity recognition within T-020 scope, no API/contract change`
- **Risks or Blockers**: `none for local verification; external reviewer must assess the new head`
- **Review Request**: `codex-review-a technical follow-up; caitoithap separate Claude re-review and peer PR approval pending`
- **Commits**: `a8fa471 (source, tests and docs); coordinator context 4bf3a17 preserved`

## Command Evidence

| L?nh | K?t qu? | B?ng ch?ng |
|---|---|---|
| `git pull --ff-only origin feat/T-020-vn-pii` | `passed` | Pulled coordinator 4bf3a17 before edits; item 5 already resolved by A |
| `gh api repos/caitoithap/bank-assistant/issues/comments/6515181908` | `passed` | Exact body archived with reviewer/source/head attribution; no new Claude approval claimed |
| `git commit source/tests/docs` | `passed` | a8fa471 |

## Verification Evidence

| Ki?m tra | K?t qu? | B?ng ch?ng |
|---|---|---|
| `Pre-fix new review regressions on Python 3.10` | `failed` | 16 failed, 4 passed; verified missing formats and F01 grouped-account adjacency |
| `Python 3.10.22 pytest tests/security/test_pii.py -q` | `passed` | 91 passed in 2.86s, Presidio 2.2.365 |
| `WSL Python 3.12 make check` | `passed` | 452 passed, 24 deselected in 102.43s; Ruff passed; FRAMEWORK_VALIDATION_PASS |

## Deviations

- **Plan Deviations**: `Numeric grouping could otherwise merge phones and independent amounts/accounts. Explicit numeric labels anchor their spans; complete phones split remaining numeric analysis into gaps. Numbers like ref0900000001 are deliberately over-masked per review. Existing final reports remain immutable.`
- **Approved By**: `not-applicable; existing user request and reviewer bounded correction requests, no baseline scope or contract change`
- **Known Limitations**: `Bare grouped digits beginning with a complete phone are ambiguous: 0900 000 001 23 becomes PHONE_NUMBER followed by 23; explicit CCCD/STK labels select the full numeric span. Numeric labels require space/tab or :/= delimiters; attached labels are supported only for phones. Full-width digits remain excluded. Names/emails may remain in audit question_masked, now documented. Archived Claude review is CHANGES_REQUESTED at 1bd48be, not approval of a8fa471; re-review required.`

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
