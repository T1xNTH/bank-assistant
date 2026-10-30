---
id: impl-t021-pr61-followup
title: T-021 PR61 preliminary review follow-up
type: report
domain: governance
module: execution
tags: [implementation, report, T-021]
priority: 2
---
# T-021 PR61 preliminary review follow-up

## Usage Purpose

Dùng template này để cung cấp bằng chứng có thể kiểm toán về công việc Executor Agent đã làm cho một task đã được phép.

## Record Metadata

- **Report ID**: `T-021-PR61-followup`
- **Title**: `Che input, output, log, audit`
- **Owner**: `teammate-b`
- **Executor**: `codex-b`
- **Status**: `complete`
- **Task ID**: `T-021`
- **Epic ID**: `E-007`
- **Report Date**: `2026-10-30`

## Scope

- **Implemented**: Address the three preliminary observations at https://github.com/caitoithap/bank-assistant/pull/61#issuecomment-6518800474 after pulling coordinator merge d4c875d. Preserve all merged T-017/main records.
- **Not Implemented**: Independent Claude review/owner approval; new recognizer semantics; routing policy. Prior final T-021 report remains immutable evidence for 5300758, not this follow-up.

## Changes Made

| File ho?c s?n ph?m | T?m t?t thay ??i | Task ID |
|---|---|---|
| `src/app/log_config.py` | Mask rendered message and application extras once per record. Skip standard source/formatter metadata. Private identity marker avoids repeat work across handlers and formatter; standalone formatter invokes filter when needed. Clear cached raw message, exception and stack data. Preserve access-log metadata while discarding URL/client data. | `T-021` |
| `tests/api/test_request_logging.py` | Count exactly three masker calls for message + two extras across repeated handlers/formatting. Verify source metadata unchanged, no raw cached message, and generated ISO/standard asctime timestamps remain intact alongside masked CCCD. | `T-021` |
| `src/app/security/masking.py`, `src/app/main.py` | Strict input masking raises safe MaskingError; /ask and /chat return generic 503 without calling answerer/LLM on masker exception or invalid result. Log/audit/output sinks retain fail-closed REDACTED fallback. | `T-021` |
| `tests/security/test_no_pii_leak.py`, `tests/security/test_audit.py` | Masker failures now assert 503, zero backend calls and one safe audit row with unknown route/refusal; retain byte/log leak scans. | `T-021` |

## Related Files

- **Task Records**: `.agent/execution/tasks/T-021.md`
- **Context Packages**: Preliminary comment https://github.com/caitoithap/bank-assistant/pull/61#issuecomment-6518800474; `docs/02-architecture/architecture.md`; `src/app/log_config.py`, `src/app/security/masking.py`
- **Task Board**: `.agent/execution/task-board.md`
- **Current Context**: `.agent/execution/current-context.md`
- **Decisions**: `.agent/governance/decisions/DEC-004.md`
- **Change Requests**: none; bounded implementation correction within T-021
- **Risks or Blockers**: none for WSL verification
- **Review Request**: `claude-review-a`
- **Commits**: `0bac953`; mapped in `.agent/intelligence/git-nexus/task-commit-map.md`

## Command Evidence

| L?nh | K?t qu? | B?ng ch?ng |
|---|---|---|
| `git pull --ff-only` | passed | Pulled coordinator merge d4c875d, preserving T-017/main integration |
| `pytest tests/api/test_request_logging.py tests/security/test_no_pii_leak.py tests/security/test_audit.py -q -x` | passed | WSL: 48 passed in 17.12s before final cached-message hardening |
| `make check PY=/home/viet_anh/.venvs/bank-t011/bin/python` | passed | Final full WSL check: 531 passed, 29 deselected in 109.71s, Ruff passed, FRAMEWORK_VALIDATION_PASS |

## Verification Evidence

| Ki?m tra | K?t qu? | B?ng ch?ng |
|---|---|---|
| Final WSL make check | passed | 531 passed, 29 deselected in 109.71s on 0bac953 source; Ruff and FRAMEWORK_VALIDATION_PASS |
| `git diff --check` | passed | No whitespace errors |
| Native Windows | not-run | Existing Presidio/Python3.13 debug-log crash documented in original report; use established WSL Python environment |

## Deviations

- **Plan Deviations**: User explicitly requests fixes to preliminary external feedback. Task resumes review -> in-progress as coordinator; old final reports remain intact. That feedback explicitly states it is not a full DEC-004 review.
- **Approved By**: User-authorized correction; no new external technical approval claimed.
- **Known Limitations**: Logger source metadata is fixed code metadata, not a payload channel. Application data belongs in message/extra fields. Sanitized records are shared by handlers; handlers must not replace payload after sanitization. Generated timestamp/asctime fields are preserved; date-like text inside arbitrary customer messages still uses the conservative T-020 numeric recognizers. Request input failures now return 503 before backend calls, while sink failures redact. Structured /chat backend errors and input-mask errors share the existing safe 503 envelope. Queue/trace implementation and PII-based routing remain separate tasks.

## Completion Criteria

- [x] Every change maps to user-authorized T-021 feedback.
- [x] Final validation results and acceptance evidence recorded.
- [x] Deviations and limitations are explicit.
- [x] Commit mapping updated.
- [x] Independent review remains pending under DEC-004.

## Forbidden Actions

- Không báo cáo việc chưa làm là đã hiện thực.
- Không bỏ sót kiểm tra bắt buộc bị fail hoặc chưa chạy.
- Không tuyên bố hoàn thành khi acceptance criteria của task chưa đạt.
- Không tuyên bố review đã duyệt hay chuyển task sang `DONE`.
- Không đổi roadmap hay acceptance criteria.
- Không dùng report này thay cho review độc lập.
- Không đưa secret hay output lệnh nhạy cảm vào.

## Output Requirements

- Lưu thành `.agent/reports/implementation/T-021.md`.
- Giữ nguyên mọi heading và cột bảng trong template này.
- Chỉ đặt trạng thái `complete` sau khi các completion criteria đều đạt.
