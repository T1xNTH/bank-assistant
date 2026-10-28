---
id: issue-010
title: Native Windows logging runtime crash
type: governance
domain: governance
module: templates
tags: [issue, template]
priority: 3
---
# ISSUE-010: Native Windows logging runtime crash

## Usage Purpose

Track a native runtime crash separately from ISSUE-009 POSIX/encoding failures.

## Record Metadata

- **Issue ID**: `ISSUE-010`
- **Title**: `Native Windows Python 3.13 logging access violation`
- **Owner**: `teammate-b`
- **Reporter**: `codex`
- **Status**: `triaged`
- **Issue Type**: `defect`
- **Priority**: `2`
- **Created Date**: `2026-10-28`
- **Target Date**: `none`

## Description

Windows Python 3.13 crashes with access violation inside logging.LogRecord.__init__ at asyncio.current_task().get_name(). Root cause is unconfirmed. Plain logging before TestClient succeeds; logging after TestClient can crash. Do not infer that ISSUE-009 explains this defect.

## Impact

- **Affected Scope**: `native Windows API tests / Python logging`
- **Severity**: `medium`
- **User or Delivery Impact**: `Native Windows suite is not verified; Docker/WSL Linux is verified.`

## Reproduction Evidence

- **Preconditions**: `Windows, repository .venv Python 3.13, current installed Starlette/httpx2/AnyIO`
- **Steps**: `PYTHONPATH=src python -X faulthandler -m pytest -q tests/api tests/unit`
- **Observed Result**: `Initial crash at httpx2 INFO logging; disabling HTTP client INFO allows 21 tests before logging formatter test crashes at the same CPython line 383.`
- **Expected Result**: `28 tests pass without process crash`
- **Evidence Paths**: `.agent/reports/implementation/T-004.md`

## Related Files

- **Affected Files**: `src/app/logging.py, tests/api/test_request_logging.py`
- **Tasks or Epics**: `T-004, E-002`
- **Decisions**: `none`
- **Risks**: `none`
- **Blockers**: `none`

## Acceptance Criteria

- [ ] Identify runtime/dependency cause with minimal reproduction.
- [ ] API/unit suite passes on a clean supported native Windows environment.
- [ ] Linux suite remains green.

## Resolution

- **Resolution Type**: `not-applicable`
- **Resolution Summary**: `Unresolved; use WSL/Docker for task verification. No global logging workaround applied.`
- **Verification Evidence**: `none`
- **Resolved By**: `none`
- **Resolved Date**: `none`

## Completion Criteria

- [ ] Acceptance criteria pass.
- [ ] Root cause/fix and regression evidence recorded.

## Forbidden Actions

- Không đóng issue khi chưa có bằng chứng giải quyết hoặc hướng xử lý được duyệt.
- Không xoá lịch sử khi trạng thái hay owner thay đổi.
- Không gộp các vấn đề không liên quan vào một issue.
- Không bịa bằng chứng tái hiện hay kiểm chứng.

## Output Requirements

Store as `.agent/governance/issues/ISSUE-010.md`.

## Verified Workaround (2026-10-28, PR #34 follow-up)

Use a separate native Windows CPython 3.11.11 venv matching Docker's 3.11 minor version. Installed with `uv python install 3.11 --install-dir D:/bank-assistant/.venv/python-runtimes`, then `uv venv --python <3.11 interpreter> .venv/win311` and requirements-dev.txt. `python -m pytest -q tests/api tests/unit`: 29 passed in 2.56s. No 3.13 crash was observed in this run.

Python 3.13 native Windows is not a verified/supported development setup for this task; prefer 3.11 or WSL. This is a verified workaround, not a proven root-cause fix. The package `requires-python >=3.10` is unchanged because no general cross-platform 3.13 incompatibility is established. Full native Windows framework checks remain separate ISSUE-009. ISSUE-010 stays triaged rather than closed; original failure evidence above remains valid for the original environment/commit.
