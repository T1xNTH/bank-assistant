---
id: impl-t028-pr87-fixes
title: T-028 PR87 review follow-up
type: report
domain: platform
module: agent-storage
tags: [T-028, PR87, seed, sqlite]
priority: 2
---
# T-028 PR87 review follow-up

## Record Metadata

- **Task ID**: `T-028`
- **Epic ID**: `E-011`
- **Owner**: `teammate-b`
- **Executor**: `codex-b`
- **Status**: `complete`
- **Date**: `2026-11-02`
- **Review**: https://github.com/T1xNTH/bank-assistant/pull/87#issuecomment-6568381297
- **Prior Evidence**: `.agent/reports/implementation/T-028.md` (immutable original implementation evidence)
- **Implementation Commit**: `53834e4` (mapped in Git Nexus)

## Scope and Changes

1. Seed into a same-directory temporary SQLite database, close the committed
   connection, then publish with `os.link`. Existing destinations (including a
   concurrent winner) are never replaced. The temporary path is removed in
   `finally`; failures before publication leave no destination. Regressions inject
   failures at connection, transaction insertion and publication, then retry
   successfully. Another regression races two seeds and checks exactly one winner.
2. README explains the host/container path distinction and gives a Bash/WSL
   command streaming the host script into `docker compose exec -T api python -`,
   writing `/app/data/core_banking.db` in the existing API volume. No image change
   is needed for this manual step. Automatic initialization belongs to owner B's
   T-031 integration; T-041 must verify the clean-clone/empty-volume path (NFR-10).
3. README gives the API key generation command for `synthetic-user-1`, with the
   department/role and authentication setting. No keys were generated or exposed.

The separate question of self-approval is unchanged, pending owner A's decision
as requested by the reviewer. No new approval policy or ticket behavior is added.
The branch already includes main 3d5aaed via bf5657b; unrelated release metadata
from that merge is preserved.

## Verification Evidence

- Focused SQLite tests: `39 passed in 3.77s` (four new regression cases).
- Ruff: `All checks passed!`.
- WSL `make check PY=/home/viet_anh/.venvs/bank-t011/bin/python`: `804 passed,
  50 deselected in 122.42s`; Ruff pass; `FRAMEWORK_VALIDATION_PASS`.
- `git diff --check`: passed before implementation commit.
- Docker deployment: not run; container setup documentation only, with script
  content passed over stdin and existing Compose working directory/volume paths.

## Outcome

All three requested fixes are implemented, validated and mapped to commit 53834e4.
T-028 stays in review. Independent Claude re-review and counterpart PR
approval remain pending; no approval or done transition is claimed.
