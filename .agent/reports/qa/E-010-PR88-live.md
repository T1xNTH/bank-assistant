---
id: qa-e010-pr88-live
title: PR88 live Qdrant and model QA supplement
type: report
domain: testing
module: routing
tags: [qa, E-010, T-026, PR88, live]
priority: 2
---
# PR88 live Qdrant and model QA supplement

## Usage Purpose

Supersedes the unavailable-live-environment limitation in E-010-PR88.md, while
preserving that original report. User explicitly requested running the remaining
live checks. Technical test evidence only; no independent review, owner contract
approval, task transition or release authorization is inferred.

## Record Metadata

- **Report ID**: `E-010-PR88-live`
- **Title**: `Real retrieval, gateway, local model and legacy worker routing`
- **Owner**: `trong-hung`
- **Tester**: `codex`
- **Status**: `passed`
- **Task ID**: `T-026`
- **Review Decision**: `formal approval pending; technical recheck has no open routing finding`
- **Test Date**: `2026-11-02`
- **Environment ID**: `WSL; Qdrant 1.12.4; LiteLLM 1.106.6; Ollama 0.40.13 / qwen2.5:3b`

## Test Scope

- **Features or Requirements**: T-026 sensitive routing; existing live /ask regression suite.
- **Included Test Levels**: integration, API, actual model inference, real Redis worker.
- **Behavior Checks**: real bge-m3 query embeddings, Qdrant retrieval, bge-reranker-v2-m3 in existing tests, authenticated cloud gateway calls, local inference for force_local/CCCD/phone/account/confidential, and legacy masked jobs.
- **Edge Cases**: stopping the actual local model server yields 503 without cloud fallback.
- **Regression Checklist**: 16 existing live /ask cases and 8 independent live routing probes.
- **Excluded Checks**: exhaustive local-model accuracy evaluation, long-running load testing, production deployment.

## Related Files

- **Test Plan or Strategy**: tests/integration/test_ask.py; output/pr88-qa/test_live_routing.py.
- **Implementation Report**: PR branch .agent/reports/implementation/T-026.md and T-026-PR88-fixes.md.
- **Review Report**: PR branch .agent/reports/review/T-026-PR88-round-2.md.
- **Task Board**: PR branch .agent/execution/task-board.md; unchanged.
- **Current Context**: PR branch .agent/execution/current-context.md; unchanged.
- **Issues or Risks**: local response quality and cold-request latency observations below.
- **Build or Commit**: a2b7cd8e1733b0018799fec2f39c02303d0c2513; no application code modified.

## Command Evidence

| Command | Result | Evidence |
|---|---|---|
| docker start pr66qa-qdrant-1 pr66qa-litellm-1 | passed | restored existing QA services on 127.0.0.1:16366 and 127.0.0.1:14066 |
| start isolated pr88qa-ollama using existing bank-t011_ollama_data | passed | qwen2.5:3b, model ID 357c53fb659c; network alias ollama |
| live.py --test | passed | 16 passed in 168.97s; output/pr88-qa/live-ask.xml |
| live.py --routing | passed, final corrected probe run | 8 passed in 81.96s; output/pr88-qa/live-routing.xml |
| compare gateway configuration hashes | passed | live mounted config and PR config SHA256 EA096C592DBC44F0A7B07EFEFFBE6A1981B256B4D04747B3153DF2A2FEABA985 |
| agent qa start/pass/fail T-026 | not-run | no lifecycle change or approval claimed |

The first independent routing probe run had 6 assertion failures and 2 passes:
the QA probe incorrectly required the response model string to contain qwen.
LiteLLM returns its configured local-chat alias. All six calls had already
selected local and completed successfully. Corrected the probe to accept the
alias and independently assert qwen2.5:3b is loaded in the real Ollama server;
the complete rerun passed. Initial XML is preserved as live-routing-initial.xml.
No product code was changed to obtain passing results.

## Test Results

| Check ID | Level | Result | Evidence | Defect ID |
|---|---|---|---|---|
| LIVE-01 | live API/retrieval/cloud | passed | 16 original cases, actual 2815-point snapshot, query/rerank models and gateway | none |
| LIVE-02 | live sensitive routing | passed | public to cloud; force_local, CCCD, phone, account and confidential to real local model; 6 cases | none |
| LIVE-03 | live Redis worker | passed | legacy payload with masked CCCD and force_local=false selected local; 1 case | none |
| LIVE-04 | live failure handling | passed | stop Ollama; /ask returns 503 after about 30.4s; no cloud fallback; restart Ollama in cleanup | none |

## Result Summary

- **Total**: `24`
- **Passed**: `24`
- **Failed**: `0`
- **Blocked**: `0`
- **Skipped**: `0`

Combined with the previous 124 passing technical checks: 148 final passing
checks, with the previous 16 skips now replaced by live passes. These are scoped
QA checks, not additional full-suite tests or a model quality benchmark.

## Defects and Risks

- **Open Defects**: no routing defect found.
- **Residual Risks**: the real 3B model returned found=false for the synthetic phone/account prompts despite available fee context. Routing and masking passed; answer usefulness for those prompts is not established. The first local request in the initial run took about 25.4s; subsequent successful local API requests in the final run took about 1.4-3.3s. No latency SLO or exhaustive accuracy signoff is claimed.
- **Blocking Conditions**: no remaining unavailable-Qdrant or skipped-live-test limitation; formal owner approvals remain outside this technical QA run.

The original snapshot collection was not modified. Synthetic routing checks used
a uniquely named temporary collection, removed in teardown. The Redis container
created for the legacy-job probe was also removed. Qdrant, LiteLLM and Ollama
remain running; unrelated application containers were not changed.

## Acceptance Criteria

- [x] All 16 formerly skipped live checks ran and passed.
- [x] PII, confidential, force_local and legacy-job routing exercised actual local inference.
- [x] Actual local-server outage does not produce a cloud answer.
- [x] Counts, harness correction and residual observations are recorded.
- [ ] Required independent review and owner approvals recorded separately.

## Release Recommendation

- **Recommendation**: `conditional-go`
- **Conditions**: complete the required independent review/owner contract approvals. Preserve the documented local-model quality and first-request latency limitations; routing QA is not model quality or performance acceptance.
- **Rationale**: all scoped live functional/routing checks pass, with no skipped checks; real-model usefulness and performance have the limitations above.
- **Authorized By**: pending owner release decision.

## Completion Criteria

- [x] All scoped live checks ran and evidence was saved.
- [x] Earlier skipped checks are resolved by evidence, not waived.
- [x] Remaining quality/performance observations and approval boundaries are recorded.

## Forbidden Actions

Do not use this technical QA result as owner approval or as an exhaustive
evaluation of local-model answer quality or response-time requirements.

## Output Requirements

Preserve this supplement and the original report. XML and independent probes are
stored under output/pr88-qa. No credentials are included in the evidence.
