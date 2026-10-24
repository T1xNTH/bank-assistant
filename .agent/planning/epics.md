---
id: epics-v1
title: Epics
type: planning
domain: governance
module: planning
tags: [epics, planning]
priority: 2
---
# Epics

## Purpose

Maintain the authoritative registry of bounded delivery outcomes that may be expanded into executable tasks.

## Status Model

- **Valid Statuses**: `EPIC_PROPOSED | EPIC_READY | EPIC_IN_PROGRESS | EPIC_BLOCKED | EPIC_DONE | EPIC_CANCELLED`

## Epic Records

| Epic ID | Milestone ID | Outcome | Owner | Status | Task IDs | Acceptance Evidence | Governance Links |
|---|---|---|---|---|---|---|---|

| `E-001` | `M-001` | `Baseline SRS, contract, architecture; src/app/contracts.py + tests/fakes.py` | `trong-hung` | `EPIC_PROPOSED` | `none` | `pending` | `.agent/governance/decisions/DEC-001.md` |
| `E-002` | `M-001` | `Platform foundation: Docker, compose (api, qdrant, redis), CI check job, branch protection` | `teammate-b` | `EPIC_PROPOSED` | `none` | `pending` | `.agent/governance/decisions/DEC-001.md` |
| `E-003` | `M-001` | `FR-01 ingest: docling -> chunk -> bge-m3 dense+sparse -> Qdrant with full payload; 30 PDFs + manifest` | `trong-hung` | `EPIC_PROPOSED` | `none` | `pending` | `.agent/governance/decisions/DEC-001.md` |
| `E-004` | `M-001` | `FR-02 retrieval + /ask: hybrid RRF, rerank, citations, refusal threshold` | `trong-hung` | `EPIC_PROPOSED` | `none` | `pending` | `.agent/governance/decisions/DEC-001.md` |
| `E-005` | `M-001` | `FR-04a LLM gateway: LiteLLM + Ollama, llm.chat(), aliases` | `teammate-b` | `EPIC_PROPOSED` | `none` | `pending` | `.agent/governance/decisions/DEC-001.md` |
| `E-006` | `M-001` | `FR-05 auth (hashed API keys -> User), RBAC model, audit log` | `teammate-b` | `EPIC_PROPOSED` | `none` | `pending` | `.agent/governance/decisions/DEC-001.md` |
| `E-007` | `M-001` | `FR-06 PII masking on input, output, log, trace, queue` | `teammate-b` | `EPIC_PROPOSED` | `none` | `pending` | `.agent/governance/decisions/DEC-001.md` |
| `E-008` | `M-001` | `FR-03 eval: 50-question golden set, RAGAS, 3 modes, report, thresholds` | `trong-hung` | `EPIC_PROPOSED` | `none` | `pending` | `.agent/governance/decisions/DEC-001.md` |
| `E-009` | `M-001` | `FR-09 job queue: /ask/jobs, rate-limited worker, retry/backoff, priority, 503, per-key limit` | `teammate-b` | `EPIC_PROPOSED` | `none` | `pending` | `.agent/governance/decisions/DEC-001.md` |
| `E-010` | `M-002` | `FR-04b + FR-02: sensitive routing to local, RBAC filter in retrieve, superseded filter` | `trong-hung` | `EPIC_PROPOSED` | `none` | `pending` | `.agent/governance/decisions/DEC-001.md` |
| `E-011` | `M-002` | `FR-07 agent: LangGraph, 3 tools, HITL interrupt, SQLite ro, /agent endpoints` | `trong-hung` | `EPIC_PROPOSED` | `none` | `pending` | `.agent/governance/decisions/DEC-001.md` |
| `E-012` | `M-002` | `FR-08 n8n: intake -> classify -> /ask -> approval -> reply; error workflow` | `teammate-b` | `EPIC_PROPOSED` | `none` | `pending` | `.agent/governance/decisions/DEC-001.md` |
| `E-013` | `M-002` | `FR-10 observability: Langfuse traces, tokens, cost, p95, queue wait; /feedback` | `teammate-b` | `EPIC_PROPOSED` | `none` | `pending` | `.agent/governance/decisions/DEC-001.md` |
| `E-014` | `M-002` | `Quality loop: fix 3 worst answers from traces, rerun eval to meet NFR-01..04` | `trong-hung` | `EPIC_PROPOSED` | `none` | `pending` | `.agent/governance/decisions/DEC-001.md` |
| `E-015` | `M-002` | `FR-11 release hardening: CI eval gate, trivy, compose profiles, Qdrant backup, clean-clone test` | `teammate-b` | `EPIC_PROPOSED` | `none` | `pending` | `.agent/governance/decisions/DEC-001.md` |
| `E-016` | `M-002` | `FR-12 demo UI (Streamlit) + README + ADRs` | `trong-hung` | `EPIC_PROPOSED` | `none` | `pending` | `.agent/governance/decisions/DEC-001.md` |
