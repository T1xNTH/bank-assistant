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
- **Status**: `complete`
- **Task ID**: `T-011`
- **Epic ID**: `E-005`
- **Report Date**: `2026-10-29`
- **Completion Outcome**: `Implemented; controlled and real OpenAI verification passed; independent review pending`

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
| `.env.example`, root git-ignored `.env.local` | OPENAI_MODEL=gpt-6-luna; OPENAI_API_KEY field added; Gemini variables removed; key subsequently configured privately by explicit user instruction | `T-011` |
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
- **Risks or Blockers**: `BLOCKER-003 resolved; RISK-003 remains monitored`
- **Review Request**: `claude-review-a; local handoff recorded in task board/session history, independent review has not run`
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
- Initial real OpenAI verification was blocked by an empty key. The user later explicitly supplied a credential for this verification, and the real acceptance below passed. The 5-10 representative-query cost sample and spending-control verification remain prerequisites for the first full evaluation.

### Real provider follow-up

- Actual OpenAI API model access verified for gpt-6-luna using the configured key without printing credential data.
- Real pinned LiteLLM on host port 4000: `scripts/smoke_llm.py --models cloud-chat` passed; 13 input / 4 output tokens, estimated standard USD 0.00000330.
- Real strict JSON-schema smoke: `scripts/smoke_llm.py --models cloud-chat --structured` passed and validated the reply against the required pong structure; 43 input / 11 output tokens, estimated standard USD 0.00000980.
- Total: 56 input + 15 output tokens, estimated standard cost USD 0.00001310. This is a synthetic two-request sample, not the representative evaluation sample required before full eval.
- Runtime evidence: `output/t011-openai-real-smoke.log`, `output/t011-openai-real-up.log`; sensitive error bodies/key values are not included.
- BLOCKER-003 resolved; lifecycle CLI resumed task. Dedicated runtime containers/network were removed after verification. Local handoff to claude-review-a is recorded without changing the immutable canonical Gemini report; the CLI has no supplement-report target. No actual independent review or approval is claimed.

## Deviations

- **Plan Deviations**: The low-cost model role requested by CR-008 uses its current
  economical successor `gpt-6-luna` rather than deprecated GPT-4o mini. Provider and
  public contract remain exactly as approved. OPENAI_MODEL is configurable.
- **Approved By**: CR-008 authorizes the provider change; user explicitly requested it.
- **Known Limitations**: The key/model supported the two small real tests; production quota, full-evaluation budget and independent review remain unverified. Credential was supplied by explicit user instruction; no value is tracked. Root framework validation also encounters 5 pre-existing untracked local review reports with invalid/missing statuses; clean worktree validation passes. Those historical reports were preserved.

## Completion Criteria

- [x] Source implementation linked to authorized task and CR-008.
- [x] Automated and controlled gateway evidence recorded.
- [x] Final Gemini report preserved; new evidence has a separate report.
- [x] Real OpenAI plain and structured smoke passed.
- [x] Independent review handoff prepared; approval is pending and task remains review.

## Forbidden Actions

No secret values, fabricated real-provider evidence, self-approval, or task closure.

## Output Requirements

This final implementation report preserves the prior Gemini report. Independent review of the OpenAI follow-up is still required; corrections to this final report must use a supplement.
