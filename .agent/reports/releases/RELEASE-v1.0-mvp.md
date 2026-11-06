---
id: release-v1-0-mvp-qa
title: v1.0-mvp release QA and NFR evidence
type: report
domain: releases
module: execution
tags: [release, t-041, nfr, v1-0-mvp]
priority: 2
---
# Release QA v1.0-mvp

## Usage Purpose

T-041 release-readiness evidence for issue #82. This is a QA candidate report,
not authorization to publish a release or deploy production. It combines newly
executed startup/regression checks with clearly identified earlier real-model evidence.

## Record Metadata

- **Report ID**: `RELEASE-v1.0-mvp`
- **Release Version**: `v1.0-mvp (candidate; not tagged)`
- **Title**: `Clean-clone startup and NFR-01..10 evidence`
- **Owner**: `teammate-b`
- **Release Manager**: `pending owner authorization`
- **Author**: `codex-b (executor; technical QA evidence)`
- **Status**: `planned`
- **Target Environment**: `GitHub ubuntu-latest clean-clone QA; WSL Ubuntu 24.04 scoped regression`
- **Planned Date**: `2026-11-06`
- **Actual Date**: `pending`

## Release Scope

- **Included Epics or Tasks**: `T-041, E-015; NFR evidence from merged T-001..T-040/T-042`
- **Included Commits**: `main 7ab8767289ca3c30cb6f5b8b4ff0abb9aa9e10ec; T-041 documentation/evidence follow-up`
- **Included Artifacts**: `README.md, infrastructure/compose.yaml, Dockerfile pip network tolerance, scripts/smoke_release.py, release-qa.yml, docs/09-testing/evidence/T-041-eval-summary.json`
- **Excluded or Deferred Items**: `Production deployment, tag/publish, load/penetration tests, new paid/full real-model evaluation, local-model latency optimization`

## Related Files

- **Implementation Reports**: `../implementation/T-041.md`, `../implementation/T-038.md`, `../implementation/T-039-PR107-verification.md`
- **Review Reports**: `T-041 independent review pending; ../review/T-031.md, ../review/T-040.md; prerequisite GitHub approvals in ../implementation/T-041-dependency-closure.md`
- **QA Reports**: `../qa/T-040.md`, `../qa/E-009.md`, `../../../docs/12-ai/rag-eval-notes.md`
- **Change Requests**: `none; thresholds/contracts/requirements unchanged`
- **Decisions**: `DEC-001, DEC-004; existing T-038 route-specific latency deviation attributed to A`
- **Risks and Known Issues**: `NFR-08 local/mixed latency gap; finite retry budget; agent API lacks token bucket; single-process approval locking; final release authorization pending`

## Readiness Checks

- [x] T-041 implementation verification complete (code candidate 4deab88).
- [ ] T-041 independent review and counterpart approval recorded.
- [ ] Release owner accepts remaining limits and issues a release decision.
- [x] Clean-clone startup, smoke and demo evidence recorded.
- [x] Prior dependency approvals/merges linked without inventing new approvals.

## NFR-01..10 Evidence

Thresholds below preserve [the SRS](../../../docs/01-business/srs.md). PASS means
the stated test/evidence scope passed; it is not a guarantee for arbitrary future inputs.

| NFR | Requirement | Evidence and result | Disposition |
|---|---|---|---|
| NFR-01 | Faithfulness >= 0.80 | Saved 50-question T-038 hybrid_rerank **0.8929**, 35/35 answered questions scored; dense 0.901, hybrid 0.8286. Recomputed with current runner, not rejudged. | PASS, prior real-model evidence |
| NFR-02 | Retrieval hit@5 >= 0.75 | Same saved golden results: **0.90** (36/40 in-scope), dense 0.875, hybrid 0.90. | PASS, prior real-model evidence |
| NFR-03 | Out-of-scope refusal >= 90% | Same saved results: **1.0** (10/10) in every mode, zero execution errors. | PASS, prior real-model evidence |
| NFR-04 | Every answered in-scope question cites | Same saved hybrid_rerank results: **1.0** (35/35); missing/invalid citations cause refusal. In-scope answer rate is 35/40, not 100%. | PASS, prior real-model evidence |
| NFR-05 | Zero raw PII in logs/traces/queue | Current scoped regression **411 passed, zero skipped**, including security, audit, routing and persisted-job checks. `test_no_pii_leak.py` scans actual captured logs/SQLite. Full CI quality also passed; no new live Langfuse log scan is claimed. | PASS in exercised regression scope |
| NFR-06 | Zero cross-department RBAC leaks | Same 411 passing tests include real in-memory Qdrant with controlled embeddings and public/credit/hr filters. Fresh-container demo also returns zero foreign-account transactions. T-038 reports 53 earlier live integration passes including corpus RBAC. | PASS; current controlled tests plus prior corpus evidence |
| NFR-07 | Every ticket write requires approval | Same 411 passing tests include `tests/api/test_agent.py` / `test_agent_graph.py`: no write before approval/rejection, staff/self denied, authenticated owner binding and one write under concurrent decisions. | PASS in exercised regression scope |
| NFR-08 | OpenAI /ask p95 < 10 s, Langfuse | Prior 50-HTTP-trace T-038 result: **cloud 8.746 s** (45), local 21.899 s (5), combined **19.185 s**. A accepted route-separated reporting on 2026-11-04; mixed/local latency remains unmet. No latency inferred from fake demo or in-process eval. | PASS for recorded OpenAI route; mixed/local gap disclosed, no new waiver |
| NFR-09 | Burst provider 429 handled by queue/retry | **5/5 real Redis/RQ integration tests passed**, including two typed synthetic 429 failures in each of 30 jobs: all 30 done, three attempts each, zero failed jobs. Retry budget/exhaustion separately covered by passing policy tests. | PASS for tested bounded-retry pattern |
| NFR-10 | Fresh clone -> make up healthy | [Clean-clone CI 42152418148](https://github.com/T1xNTH/bank-assistant/actions/runs/42152418148), candidate 4deab88 / tested PR merge 39031cdc: all five services healthy, Make smoke, fake HTTP demo, seed/owner isolation/read-only checks, repeat-seed rejection, unchanged seed checksum after restart. Empty directory and volumes asserted; no provider key or corpus. | PASS on documented hosted Linux environment |

### Quality evidence provenance

[Saved-eval summary](../../../docs/09-testing/evidence/T-041-eval-summary.json) includes SHA-256 of each
50-row JSONL and metrics computed by current `eval/run.py` `Record`, `metrics`
and `failures` against unchanged thresholds. Golden membership, sources,
in-scope labels and department assignment were checked for all 150 rows.
This is recomputation of T-038 evidence, not a fresh retrieval/LLM/judge run.

[Live CI 42146572547](https://github.com/T1xNTH/bank-assistant/actions/runs/42146572547)
on the merged T-039 source also passed the public 10-question gate: all four
quality metrics 1.0, 8/8 answered/scored. That smoke subset does not replace the
full golden set, confidential/local model or RBAC checks.

NFR-05..07 tests use controlled model outputs/dependencies. They verify enforcement
and persistence behavior; no new end-to-end live Langfuse or full-corpus QA is claimed.
NFR-09 proves bounded recovery from the exercised synthetic 429 pattern, not
unlimited recovery from provider outages. `/ask` may expose its own 429 after
bounded retries; clients needing queue recovery must use `/ask/jobs`.

Current [CI 42152418072](https://github.com/T1xNTH/bank-assistant/actions/runs/42152418072)
at 4deab88 passed all six jobs: **1291 tests**, 81 integration deselections,
Ruff/framework validation, backend smoke/Trivy, UI syntax and real public eval.
The current 10-question gate scored faithfulness **0.875**, hit/refusal/citation
**1.0**, 8/8 answered and scored, zero errors/retries. Median judging reduces
noise without guaranteeing a deterministic score; the earlier 1.0 is a separate run.

[Scoped regression summary](../../../docs/09-testing/evidence/T-041-regression-summary.json)
retains the 411-case module counts and five real-worker case names with JUnit
checksums. Commands: `python -m pytest tests/security tests/api/test_agent.py
tests/unit/test_agent_graph.py tests/unit/test_retrieve.py tests/unit/test_queue_policy.py
tests/api/test_jobs.py tests/api/test_ask_routing.py -q` (**411 passed**, 83.90s),
then `python -m pytest -m integration tests/integration/test_worker.py -q`
(**5 passed**, 48.45s). The 411 tests overlap the 1291-test CI suite; do not add them.

### Fresh-clone evidence

[Startup summary](../../../docs/09-testing/evidence/T-041-startup-summary.json)
retains the tested merge commit, five healthy service states, before/after demo
results and SHA-256 of raw artifact files. Artifact `release-qa-42152418148-1`
contains the actual build/Make smoke/demo logs, service JSON and rejected-seed error.
The workflow's clone uses `git clone --no-local` from the checked-out PR commit:
it copies tracked Git content, not the working directory, local secrets or ignored data.
The run completed in 6m34s and cleaned only its disposable project/volumes.

The initial remote clean clone of main 7ab8767 on WSL failed during the PyTorch
wheel download before any startup acceptance. A second local candidate build at
7423770 was interrupted by the user turn interruption (`make ... Hangup`); it is
not a pass or an application failure. Hosted clean-clone success above is the
NFR-10 acceptance evidence. Fully offline or future unconstrained dependency
resolution is not guaranteed by this run.

## Deployment Plan

- **Procedure Path**: `README.md Quick start; synthetic banking stores; optional profile guides`
- **Responsible Owner**: `teammate-b`
- **Start Criteria**: `Fresh checkout, Bash/Make/Python3/curl/Docker Compose, free loopback ports, private .env.local with gateway key`
- **Success Criteria**: `Five core services healthy; make smoke; fake HTTP answer/refusal demo; explicit seed and synthetic-owner lookup`
- **Monitoring Window**: `Startup and explicit smoke/demo checks only; no production soak test`

## Rollback Plan

- **Trigger Criteria**: `Startup/smoke failure, release check failure, owner rejection`
- **Procedure Path**: `make down using the same COMPOSE_PROJECT_NAME; retain volumes and evidence; use prior approved checkout for a subsequent start`
- **Responsible Owner**: `teammate-b`
- **Recovery Verification**: `Re-run make up and make smoke; Qdrant backup/restore procedure and prior three-profile drills in ../qa/T-040.md`

## Deployment Outcome

- **Outcome**: `pending`
- **Evidence**: `Candidate QA passed: clean-clone CI 42152418148, full CI 42152418072, 411 current NFR regressions and five real Redis/RQ integrations. Durable summaries in docs/09-testing/evidence/T-041-*.json; raw hosted artifact and local output/t041-tools logs retained. Actual release/deployment outcome remains pending owner approval.`
- **Incidents or Regressions**: `README host-only quick start omitted required Redis; corrected. Initial cold image build failed on PyTorch CDN read timeout; pip network tolerance raised without changing dependency requirements. Initial concurrent local make check: 1288 passed, 2 skipped, 1 tracing fork-test subprocess timeout (15 seconds); no pass claimed for that run.`
- **Post-Release Verification**: `not-run: no release/tag/production deployment performed`

## Completion Criteria

- [x] Hosted startup/demo, local regression and earlier failed/interrupted attempts recorded separately.
- [x] All ten NFRs have named evidence sources and disclosed verification limits.
- [ ] Independent review and owner readiness decision received.
- [x] Status remains planned, consistent with absence of release approval/deployment.

## Forbidden Actions

- Do not interpret fake startup as real RAG/model quality or latency evidence.
- Do not report combined/local latency as passing NFR-08.
- Do not publish, tag or mark deployed without the actual owner approval and checks.

## Output Requirements

Task T-041 explicitly names this report `RELEASE-v1.0-mvp.md`; it uses the release
template headings while recording QA readiness rather than a production release.
