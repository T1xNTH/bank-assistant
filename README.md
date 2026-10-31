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

Authenticated clients can enqueue the same body at `POST /ask/jobs` and poll
`GET /ask/jobs/{job_id}`. Queue positions start at 1; other users and expired jobs
receive 404. Redis stores masked requests/results; completed and failed jobs expire
after one hour. `REDIS_URL` selects Redis and `QUEUE_MAX_LENGTH` (default 100) limits
waiting jobs; a full or unavailable queue returns 503.
Waiting jobs expire after `QUEUE_WAITING_TTL` seconds (default 3600). Enqueue reclaims
expired queue entries even if no worker ran, across all queues under the same bound.
Owner IDs in Redis are SHA-256 pseudonyms, not anonymous
identities: short or predictable user IDs can still be guessed from their hashes.

For a local worker smoke test, run from the repository root with `src` on the Python
path: `PYTHONPATH=src .venv/bin/python -m app.queue.worker`.
Compose starts this worker with the same Redis/RAG/LLM environment as the API.
Authenticated approvers enqueue to `ask-high`; other roles use `ask-default`.
Workers consume in that priority order, then drain legacy `ask` jobs. Positions
are snapshots across those queues; continuous high-priority work can delay others.
No new request field or client-supplied priority is accepted.

`POST /ask/jobs` uses a shared Redis token bucket per authenticated API-key digest:
`API_KEY_RPM` (default 60) and `API_KEY_BURST` (default 10). Exhaustion returns the
standard 429 envelope with integer `Retry-After`; polling is not throttled.
With fake authentication the bucket is per user. Worker execution attempts share
one Redis bucket (`WORKER_RPM`, default 60, capacity 1), including retries. The LLM
client retains its own bounded HTTP retries; RPM here counts answer execution
attempts, not individual HTTP calls within an answer. Only typed gateway 429s are
retried, up to `WORKER_MAX_ATTEMPTS` (default 4), with exponential delays starting
at `WORKER_BACKOFF_SECONDS` (default 1), capped at 60s. Final failures stay sanitized.
`WORKER_JOB_TIMEOUT` (default 600s) bounds total job execution, including waits;
increase it for lower RPM or long LLM latency. Worker operations require Redis;
limiter outages fail closed. Limits must be positive integers; backoff seconds
also accepts positive finite fractions for testing or shorter retry schedules.

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
