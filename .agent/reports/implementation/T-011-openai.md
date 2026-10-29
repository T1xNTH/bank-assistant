---
id: implementation-t011-openai
title: T-011 OpenAI provider migration under CR-008
type: report
domain: platform
module: infrastructure
tags: [implementation, t-011, cr-008, openai]
priority: 2
---
# Implementation Report T-011 OpenAI follow-up

## Usage Purpose

Supplement the immutable Gemini-era [T-011 report](T-011.md). Its runtime approval
evidence does not validate this new OpenAI provider configuration.

## Record Metadata

- **Report ID**: `T-011-openai`
- **Owner**: `teammate-b`
- **Executor**: `codex-b`
- **Status**: `draft`
- **Task ID**: `T-011`
- **Epic ID**: `E-005`
- **Report Date**: `2026-10-29`
- **Completion Outcome**: `Code implemented and controlled verification passed; real OpenAI acceptance blocked by BLOCKER-003`

## Scope

- **Implemented**: Latest main 3ad1cb9 merged with prior T-011 work; cloud-chat
  migrated to OpenAI; provider credential isolation, baseline documents, CI,
  smoke CLI and tests updated under approved CR-008.
- **Not Implemented**: T-012/T-023 adapters, full evaluation, account spending
  settings, independent review, GitHub push/PR or merge.

## Changes Made

| File or artifact | Change | Task ID |
|---|---|---|
| `infrastructure/litellm/config.yaml`, Compose files | OPENAI_API_KEY only in LiteLLM; openai/OPENAI_MODEL alias; gateway/provider retries set to zero; local aliases unchanged | `T-011` |
| `.env.example`, root git-ignored `.env.local` | OPENAI_MODEL=gpt-6-luna; OPENAI_API_KEY field added; Gemini variables removed; key remains empty | `T-011` |
| `scripts/smoke_llm.py` | OpenAI max_completion_tokens and reasoning_effort=none; optional strict JSON-schema pong check; errors remain redacted | `T-011` |
| `tests/unit/test_smoke_llm.py`, gateway integration tests | OpenAI isolation, strict output validation, real pinned LiteLLM with fake OpenAI upstream; 429 generates exactly one upstream call | `T-011` |
| SRS, architecture, AI design, product plan, RISK-003, ISSUE-006, setup guide | Approved provider/budget baseline and default judge model documented; historical reports and approved CR text preserved | `T-011` |

## Related Files

- **Task Records**: `.agent/execution/tasks/T-011.md`
- **Context Packages**: approved CR-008; `docs/12-ai/ai-design.md`; `AGENT.md`
- **Task Board**: `.agent/execution/task-board.md`
- **Current Context**: `.agent/execution/current-context.md`
- **Decisions**: `DEC-001`
- **Change Requests**: `CR-008 (approved on main 3ad1cb9)`
- **Risks or Blockers**: `BLOCKER-003; RISK-003`
- **Review Request**: `pending new provider acceptance; no independent approval claimed`
- **Commits**: `3dc6c2e (merge main); e81fddfd5852640589dab8cfb0997b5d913e383a (provider migration)`

## Command Evidence

| Command | Result | Evidence |
|---|---|---|
| `git fetch origin` and fast-forward root to main | `passed` | Latest upstream 3ad1cb9, including approved CR-008 |
| `git merge origin/main` in T-011 worktree | `passed` | Resolved context/history/map conflicts preserving both histories; merge 3dc6c2e |
| `make check PY=/home/viet_anh/.venvs/bank-t011/bin/python` in WSL | `passed` | 167 passed, 17 integration deselected, 65.54s; Ruff and framework validation passed |
| `pytest -o addopts= tests/unit/test_smoke_llm.py tests/integration/test_gateway_config.py tests/integration/test_gateway_openai.py -q` in WSL | `passed` | 15 passed in 50.86s |

## Verification Evidence

- Tests use pinned real LiteLLM v1.106.6 and a local fake OpenAI HTTP server,
  with generated synthetic credentials. They incur no provider charges.
- Plain completion and strict JSON-schema smoke each produce exactly one upstream
  request. A 429 also produces exactly one upstream request and returns 429.
- Resolved Compose tests verify only LiteLLM has OPENAI_API_KEY; no service has
  GEMINI_API_KEY; CI has no provider credential or published ports; Ollama stays
  optional with persistent weights and localhost binding.
- Unit tests cover empty/wrong/malformed structured responses and secret-free
  error output. This is controlled compatibility evidence, not real model quality.
- Final source default is `gpt-6-luna`: current economical replacement for deprecated
  GPT-4o mini, supports Chat Completions and structured outputs, and costs less than
  the mini model. Official pricing checked 2026-10-29: USD 0.10/1M input and
  USD 0.50/1M output tokens for prompts up to 272K input; longer prompts cost more.
  [Official model documentation](https://developers.openai.com/api/docs/models/gpt-6-luna).
- Local logs outside git: `output/t011-openai-check.log`,
  `output/t011-openai-focused.log`. Test containers/network are removed by fixture.
- Root untracked ISSUE-017 was preserved at
  `output/pull-backup-20261029/ISSUE-017-local.md` before pulling its tracked upstream version.
- Real OpenAI ping/structured output and 5-10 real-query cost sampling: **not-run**;
  OPENAI_API_KEY remains empty. The cost sample and spending-control verification
  are prerequisites for the first full evaluation, not claims made by this task.

## Deviations

- **Plan Deviations**: The low-cost model role requested by CR-008 uses its current
  economical successor `gpt-6-luna` rather than deprecated GPT-4o mini. Provider and
  public contract remain exactly as approved. OPENAI_MODEL is configurable.
- **Approved By**: CR-008 authorizes the provider change; user explicitly requested it.
- **Known Limitations**: Real model access/billing/quota and independent review
  remain unverified. Prior exposed chat credentials were not reused.

## Completion Criteria

- [x] Source implementation linked to authorized task and CR-008.
- [x] Automated and controlled gateway evidence recorded.
- [x] Final Gemini report preserved; new evidence has a separate report.
- [ ] Real OpenAI plain and structured smoke passed.
- [ ] Independent review completed; task must not be marked done.

## Forbidden Actions

No secret values, fabricated real-provider evidence, self-approval, or task closure.

## Output Requirements

Keep this report draft until real OpenAI acceptance is recorded; request independent
review of the OpenAI changes separately from the prior Gemini implementation.
