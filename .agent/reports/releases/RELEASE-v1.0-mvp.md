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
- **Target Environment**: `local Linux Docker Engine via WSL Ubuntu 24.04`
- **Planned Date**: `2026-11-06`
- **Actual Date**: `pending`

## Release Scope

- **Included Epics or Tasks**: `T-041, E-015; NFR evidence from merged T-001..T-040/T-042`
- **Included Commits**: `main 7ab8767289ca3c30cb6f5b8b4ff0abb9aa9e10ec; T-041 documentation/evidence follow-up`
- **Included Artifacts**: `README.md, infrastructure/compose.yaml, existing API/worker image, docs/09-testing/evidence/T-041-eval-summary.json`
- **Excluded or Deferred Items**: `Production deployment, tag/publish, load/penetration tests, new paid/full real-model evaluation, local-model latency optimization`

## Related Files

- **Implementation Reports**: `../implementation/T-041.md`, `../implementation/T-038.md`, `../implementation/T-039-PR107-verification.md`
- **Review Reports**: `T-041 independent review pending; ../review/T-031.md, ../review/T-040.md; prerequisite GitHub approvals in ../implementation/T-041-dependency-closure.md`
- **QA Reports**: `../qa/T-040.md`, `../qa/E-009.md`, `../../../docs/12-ai/rag-eval-notes.md`
- **Change Requests**: `none; thresholds/contracts/requirements unchanged`
- **Decisions**: `DEC-001, DEC-004; existing T-038 route-specific latency deviation attributed to A`
- **Risks and Known Issues**: `NFR-08 local/mixed latency gap; finite retry budget; agent API lacks token bucket; single-process approval locking; final release authorization pending`

## Readiness Checks

- [ ] T-041 implementation verification complete.
- [ ] T-041 independent review and counterpart approval recorded.
- [ ] Release owner accepts remaining limits and issues a release decision.
- [ ] Clean-clone startup, smoke and demo evidence recorded.
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
| NFR-05 | Zero raw PII in logs/traces/queue | Current security, audit, routing, tracing and job tests: pending full-suite result. `test_no_pii_leak.py` scans actual captured logs/SQLite; queue tests inspect persisted Redis data. | Pending current regression |
| NFR-06 | Zero cross-department RBAC leaks | Current `test_retrieve.py` uses real in-memory Qdrant with controlled embeddings and public/credit/hr filters; agent tools enforce owner/foreign-account isolation. T-038 reports 53 live integration passes including corpus RBAC. | Pending current regression; prior corpus evidence linked |
| NFR-07 | Every ticket write requires approval | `tests/api/test_agent.py` / `test_agent_graph.py`: pending current result. Tests assert no write before approval/rejection, staff/self denied, authenticated owner binding and one write under concurrent decisions. | Pending current regression |
| NFR-08 | OpenAI /ask p95 < 10 s, Langfuse | Prior 50-HTTP-trace T-038 result: **cloud 8.746 s** (45), local 21.899 s (5), combined **19.185 s**. A accepted route-separated reporting on 2026-11-04; mixed/local latency remains unmet. No latency inferred from fake demo or in-process eval. | PASS for recorded OpenAI route; mixed/local gap disclosed, no new waiver |
| NFR-09 | Burst provider 429 handled by queue/retry | Current real Redis/RQ integration test injects two typed 429 failures into each of 30 jobs, expects all 30 done and zero failed jobs: pending execution. Retry limits/exhaustion are separately tested. | Pending current integration |
| NFR-10 | Fresh clone -> make up healthy | New clone of 7ab8767 into an empty Linux directory, fresh Compose project/volumes, generated gateway key, fake RAG/LLM/auth, no provider key or corpus. Actual make up/smoke/demo results pending. | Pending startup evidence |

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
- **Evidence**: `Local acceptance execution in progress; raw build/check logs under shared workspace output/t041-tools; sanitized durable summary will be linked here`
- **Incidents or Regressions**: `README host-only quick start omitted required Redis; corrected to Compose-first setup`
- **Post-Release Verification**: `not-run: no release/tag/production deployment performed`

## Completion Criteria

- [ ] Local startup, demo and regression results recorded.
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
