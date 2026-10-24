# bank-assistant

Internal assistant for bank staff: answers **only from internal documents** with file/page citations, refuses when the answer is not there, enforces department permissions, masks personal data, and runs a small agent (loan calculation, transaction lookup, ticket creation with human approval). API-first, integrated with n8n.

> Status: **scaffold** — roadmap `R-001` is `ROADMAP_DRAFT` until DEC-001 is approved. MVP target: 10 working days, team of two.

## Quick start
```bash
make setup                     # .venv + dev deps
cp .env.example .env.local     # fill in secrets later
make check                     # ruff + pytest + framework validation
.venv/bin/uvicorn app.main:app --app-dir src --port 8000
curl -s localhost:8000/health
curl -s -X POST localhost:8000/ask -H 'content-type: application/json' -d '{"question":"Phí thường niên thẻ?"}'
```
With fake backends (`RAG_BACKEND=fake`) `/ask` returns a canned, contract-shaped answer so the platform side can be built in parallel with RAG.

## Where things are
| Path | What |
|---|---|
| `docs/00-project/product-plan.md` | Plan: scope, epics, owners, daily schedule |
| `docs/01-business/srs.md` | Requirements FR-01..12, NFR-01..10 |
| `docs/04-api/openapi.yaml` | External contract; `src/app/contracts.py` internal contracts |
| `docs/02-architecture/architecture.md` | Components, data flow, trust boundaries |
| `docs/07-development/team-workflow.md` | How the two of us work (git, review, DoD) |
| `docs/07-development/agent-cli.md` | `scripts/agent` lifecycle commands |
| `.agent/` | Agentic SDLC Kit: planning truth, task board, governance, reports |
| `src/app/` | Code (each stub names its owner and epic) |
| `infrastructure/` | Dockerfile, compose, LiteLLM, n8n |

## Process
Managed with [Agentic SDLC Kit](https://github.com/toilatrung/agentic-sdlc-kit) (`AGENT.md` is the operating policy): Roadmap → Milestone → Epic → Task; executor (Claude Code) → independent reviewer (separate Claude Code session) → QA per epic → release report.
