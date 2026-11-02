---
id: t025-pr65-main-followup
title: T-025 PR65 main compatibility fixes
type: report
domain: development
module: queue
tags: [T-025, PR65, retry, worker]
priority: 2
---
# T-025 PR65 follow-up

## Record Metadata

- **Owner**: `teammate-b`
- **Executor**: `codex-b`
- **Status**: `complete`
- **Date**: `2026-11-01`
- **Review**: https://github.com/T1xNTH/bank-assistant/pull/65#issuecomment-6546153960
- **Note**: independent review pending; CI format fix (Record Metadata, BOM) by `claude-a`.

## Summary


Merged origin/main bb35740; preserved both session histories, main T-022/T-023 progress and branch T-024/T-025 evidence. Worker retries AnswerUnavailable only when its direct cause is LLMRateLimitError, preserving API error mapping and bounded backoff. Worker shares only hf_cache, without audit/config mounts. Existing real RagAnswerer integration covers 30 jobs each receiving two 429s. Unit regression covers direct and wrapped 429s. Compose regression requires the cache mount.

Validation: WSL make check: Ruff passed, 764 passed / 50 deselected, FRAMEWORK_VALIDATION_PASS. Focused policy regression after adding wrapped case: 19 passed. Redis/Compose integration: 8 passed in 36.25s. git diff --check clean. No independent approval or merge claimed.
