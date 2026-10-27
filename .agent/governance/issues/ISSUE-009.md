---
id: issue-009
title: "ISSUE-009: Framework tests và scripts/agent lỗi trên Windows"
type: governance
domain: governance
module: issues
tags: [issue, tooling, windows, scripts-agent]
priority: 2
---
# ISSUE-009: Framework tests và `scripts/agent` lỗi trên Windows

## Usage Purpose

Theo dõi việc B (máy Windows) không chạy được trọn `make check`: B báo trên PR #29 rằng pytest trên Windows cho `18 passed, 9 failed` do shell POSIX và encoding cp1252 trong framework tests.

## Record Metadata

- **Issue ID**: `ISSUE-009`
- **Title**: `Framework tests và scripts/agent lỗi trên Windows`
- **Owner**: `trong-hung`
- **Reporter**: `teammate-b`
- **Status**: `open`
- **Issue Type**: `defect`
- **Priority**: `2`
- **Created Date**: `2026-10-27`
- **Target Date**: `2026-10-29`

## Description

B chạy lại kiểm tra trên bản trích xuất commit `c9a8ce6` bằng Windows: Ruff pass, `FRAMEWORK_VALIDATION_PASS`, nhưng pytest `18 passed, 9 failed` do `tests/framework/` gọi shell POSIX và đọc/ghi với encoding mặc định cp1252. CI (Ubuntu) pass. Nghĩa là B không tự kiểm được lifecycle CLI (`scripts/agent`, DEC-003) trên máy mình.

## Impact

- **Affected Scope**: `scripts/agent, tests/framework/test_agent_cli.py, Makefile`
- **Severity**: `medium`
- **User or Delivery Impact**: `B không chạy được make check/agent CLI đầy đủ trên Windows; dễ lệch kết quả giữa hai máy`

## Reproduction Evidence

- **Preconditions**: `Windows, Python 3.10+, encoding mặc định cp1252`
- **Steps**: `python -m pytest -q tại commit c9a8ce6`
- **Observed Result**: `18 passed, 9 failed`
- **Expected Result**: `27 passed như trên Linux/CI`
- **Evidence Paths**: `comment của B trên PR #29: https://github.com/caitoithap/bank-assistant/pull/29#issuecomment-6434139388`

## Related Files

- **Affected Files**: `scripts/agent, tests/framework/test_agent_cli.py`
- **Tasks or Epics**: `E-002 (tooling); ảnh hưởng mọi task của B`
- **Decisions**: `.agent/governance/decisions/DEC-003.md`
- **Risks**: `none`
- **Blockers**: `none`

## Acceptance Criteria

- [ ] Tái hiện được 9 test lỗi (CI thêm job `windows-latest` hoặc chạy trên máy B).
- [ ] Test và CLI dùng `encoding="utf-8"` tường minh và không phụ thuộc shell POSIX (gọi `sys.executable` thay vì shebang, dùng lệnh verify đa nền tảng).
- [ ] Pytest pass trên cả Linux và Windows.

## Resolution

- **Resolution Type**: `not-applicable`
- **Resolution Summary**: `chưa giải quyết; tạm thời B dùng WSL2 hoặc dựa vào CI`
- **Verification Evidence**: `none`
- **Resolved By**: `none`
- **Resolved Date**: `none`

## Completion Criteria

- [ ] Acceptance criteria đạt.
- [ ] Bằng chứng giải quyết đã được liên kết.
- [ ] CI kiểm cả Windows.

## Forbidden Actions

- Không đóng issue khi chưa có bằng chứng pytest pass trên Windows.

## Output Requirements

- Lưu tại `.agent/governance/issues/ISSUE-009.md`.
- Giữ nguyên mọi heading của issue template.
