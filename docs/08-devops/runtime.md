---
id: runtime-guide
title: Runtime and Delivery
type: reference
domain: devops
module: infrastructure
tags: [devops, docker, ci]
priority: 2
---
# Runtime and Delivery

## Commands
| Command | What it does |
|---|---|
| `make setup` | create `.venv`, install `requirements-dev.txt` |
| `make check` | ruff + pytest + framework validation (what `agent task verify` runs) |
| `make up` / `make down` | compose core services (`COMPOSE_PROFILES` adds `local-llm,automation,obs`) |
| `make validate` | `python3 scripts/validate-framework.py` |
| `make backup` / `make restore` | Qdrant snapshot (FR-11) |

## CI (`.github/workflows/ci.yml`)
Job `check`: ruff, pytest (fake backends), framework validation. Added during E-015: job `eval` (gate on NFR thresholds), job `trivy`.

## Environments
Only local compose for MVP. Secrets in `.env.local` (git-ignored); `.env.example` lists every variable.
