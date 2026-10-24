---
id: project-srs
title: Software Requirements Specification — bank-assistant MVP
type: reference
domain: business
module: repository
tags: [srs, requirements, mvp]
priority: 1
---
# Software Requirements Specification — bank-assistant MVP

## Input Status

- **Status**: `ingested`
- **Authority**: `draft — pending approval in DEC-001`
- **Source Artifact**: `docs/00-project/product-plan.md` (approved by product owner 2026-10-24)
- **Ingested Date**: `2026-10-24`
- **Validated By**: `trong-hung` (A), `teammate-b` (B) — cross-review required before DEC-001

## Objectives

An internal assistant for bank staff that answers questions **only from internal documents**, always cites file and page, refuses when the answer is not in the documents, respects department permissions, never leaks personal data, and can perform a small set of actions (loan calculation, transaction lookup, ticket creation) with a human approval step. It is API-first and integrates with workflow automation (n8n).

## Scope

### Included (MVP)
FR-01 … FR-12 below. All must be delivered — no scope cut (product owner decision, 2026-10-24).

### Excluded (MVP)
- SSO/OIDC, secret manager (Vault), TLS termination, multi-replica HA, alerting/on-call, load testing, penetration testing, data-retention automation, prompt/model A/B. Out of MVP by product-owner decision (2026-10-24).
- Real customer data. Only public documents and synthetic data are used.

## Stakeholders and User Classes

| Class | Description | Department values |
|---|---|---|
| Staff user | Asks questions, uses the agent | `public`, `credit`, `hr` |
| Approver | Approves sensitive agent actions (`tao_ticket`) and n8n replies | role `approver` |
| Operator | Runs the stack, reads traces and cost | team members |
| Integrator | n8n workflows calling the API | service API key |

## Functional Requirements

| ID | Requirement | Acceptance (summary) |
|---|---|---|
| FR-01 | Ingest PDFs (docling, tables + OCR) → chunk → bge-m3 dense + sparse → Qdrant, with payload `source, page, department, classification, effective_date, superseded_by` | `scripts/ingest.py` indexes ≥ 30 public PDFs; every point has all payload fields |
| FR-02 | `POST /ask`: hybrid retrieval (dense + sparse, RRF) + bge-reranker-v2-m3, answer with citations (file, page), refuse below threshold, never cite superseded documents | Answer JSON matches contract; out-of-scope → refusal text; superseded doc never cited |
| FR-03 | Evaluation harness: 50-question golden set, RAGAS metrics, compare modes `dense`, `hybrid`, `hybrid_rerank`, written report | `eval/` runner produces `docs/12-ai/rag-eval-report.md` |
| FR-04 | LLM gateway via LiteLLM (Gemini + Ollama Qwen2.5 Q4); sensitive input routed to local model | `route` field shows `local` when PII/confidential detected |
| FR-05 | API-key auth (hashed keys) → `User(user_id, department, role)`; RBAC filter on retrieval; audit log of who asked what, when | User of `credit` never receives `hr` chunks (tests) |
| FR-06 | PII masking (Presidio + VN regex: CCCD, account number, phone) on input, output, logs, traces, queue payloads | No raw PII in logs/traces/queue (tests) |
| FR-07 | LangGraph agent with tools `tinh_lai_vay`, `tra_cuu_giao_dich` (SQLite read-only), `tao_ticket` (human approval via interrupt) | `tao_ticket` never executes without approver decision |
| FR-08 | n8n workflows: intake → classify → `/ask` → approval → reply; error workflow | Workflow JSON exported in `infrastructure/n8n/workflows/` |
| FR-09 | Job queue (Redis + RQ): `POST /ask/jobs` → 202, `GET /ask/jobs/{id}`; worker rate limit, retry/backoff on 429, priority, max queue length → 503, per-key rate limit, owner-only results | Burst over Gemini RPM completes without user-visible errors |
| FR-10 | Observability with Langfuse: traces, tokens, cost, latency p95, queue wait vs processing; `POST /feedback` | Dashboard shows the listed metrics |
| FR-11 | Delivery: CI (ruff, pytest, framework validation, eval gate, trivy), compose profiles, Qdrant backup/restore | Fresh clone → `make up` works; CI fails when eval drops below threshold |
| FR-12 | Demo chat UI (Streamlit, role selector) and documentation (README, architecture, ADRs) | Demo script runs end to end |

## Non-Functional Requirements

| ID | Requirement | Threshold | Verified by |
|---|---|---|---|
| NFR-01 | Faithfulness | ≥ 0.80 | RAGAS on golden set |
| NFR-02 | Retrieval hit@5 | ≥ 0.75 | eval runner |
| NFR-03 | Correct refusal on out-of-scope questions | ≥ 90 % | eval runner |
| NFR-04 | Answers with at least one citation (in-scope) | 100 % | eval runner |
| NFR-05 | Raw PII in logs, traces, queue | 0 occurrences | tests + log scan |
| NFR-06 | RBAC leakage across departments | 0 cases | tests |
| NFR-07 | `tao_ticket` executed with approval | 100 % | tests |
| NFR-08 | `/ask` latency p95 with Gemini | < 10 s | Langfuse |
| NFR-09 | Provider 429 under burst | 0 user-visible failures (jobs queued and retried) | queue test |
| NFR-10 | Reproducible run | fresh clone → `make up` healthy | release QA |

## Assumptions and Constraints

- Team of two, ~8 h/day each, 10 working days; Claude Code as executor agent.
- Machines: CPU only (no GPU), 15 GB RAM; Docker must be installed on day 1.
- Gemini free tier (rate-limited); local model via Ollama on CPU (slow, demo-grade).
- Python 3.10+.

## Related Files

- Contract: `docs/04-api/contract.md`
- Architecture: `docs/02-architecture/architecture.md`
- Roadmap: `.agent/planning/roadmap.md`
- Epic registry: `.agent/planning/epics.md`

## Forbidden Actions

- Do not change FR/NFR after DEC-001 is accepted without an approved change request.
- Do not use real customer data.
