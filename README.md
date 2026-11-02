# bank-assistant

Internal assistant for bank staff: answers **only from internal documents** with file/page citations, refuses when the answer is not there, enforces department permissions, masks personal data, and runs a small agent (loan calculation, transaction lookup, ticket creation with human approval). API-first, integrated with n8n.

> Status: **scaffold** — roadmap `R-001` is `ROADMAP_DRAFT` until DEC-001 is approved. MVP target: 10 working days, team of two.

## Synthetic banking stores

Run `python scripts/seed_core_banking.py` from the repository root to create
`data/core_banking.db` with three synthetic users (`synthetic-user-1` through
`synthetic-user-3`), one account each and five transactions per account. No real
customer data is used. `--path PATH` selects another file; existing files are never
overwritten. Seeding commits a temporary database in the destination directory,
then publishes it with an exclusive hard link. A failed seed removes its temporary
file and leaves no incomplete destination; rerun the same command to retry.
Amounts and balances use integer VND; transaction amounts are signed.

For manual demos, create an API key whose identity matches the seed data:
`python scripts/make_key.py --user-id synthetic-user-1 --department credit --role staff`.
Keep the printed key for the `X-API-Key` header and enable `AUTH_BACKEND=apikey`;
the registry stores its hash. This command does not change other users' identities.

The current API image does not include `scripts/` and does not seed automatically.
Its default database lives at `/app/data/core_banking.db` in the `audit_data` volume,
separate from a host-side `data/core_banking.db`. After `make up`, seed that volume
from the host checkout (Bash/WSL):

```bash
docker compose -f infrastructure/compose.yaml --env-file .env.local exec -T api \
  python - --path /app/data/core_banking.db < scripts/seed_core_banking.py
```

This streams the script into the running API without requiring it in the image.
An existing destination fails safely with `FileExistsError`; do not delete it just
to rerun setup. Owner B will wire first-run container initialization when integrating
the agent endpoints in T-031; T-041 (also B) must verify seeding and synthetic-user
lookup from a clean clone/empty volume for NFR-10. Until then, the command above is
the required manual setup step before enabling the transaction tool in Docker.

`app.agent.core_banking.CoreBanking` opens SQLite with `mode=ro`; even SQL writes
through its connection fail. `accounts(user)` and
`transactions(user, account_id=None, limit=20)` filter by the authenticated `User`;
roles do not grant access to other users' data. Transaction limits range from 1 to
100, newest first. Use `CORE_BANKING_DB_PATH` to override the default path. The tool
layer must supply the trusted user and mask output before returning it to an LLM.

`app.agent.tickets.TicketStore.create(created_by, summary, approved_by, *, decision=...)`
writes to `data/tickets.db` (`TICKETS_DB_PATH` overrides it). A `TicketDecision` must
explicitly approve the exact creator and summary and identify an authenticated
`User` with role `approver` matching `approved_by`. The approver must be a different
user from `created_by`; users cannot approve their own tickets. Missing, rejected or mismatched
decisions fail before a database is opened. Created tickets have status `open` and
a UTC timestamp. Construct decisions only in the trusted approval handler after
resolving the pending proposal, never from model or tool arguments. Persistent
decisions, thread ownership and replay prevention are integration work for T-030
and T-031; these storage modules do not provide agent endpoints.

## Agent tools (T-029)

Construct `AgentTools(authenticated_user)` from `app.agent.tools` per request;
T-030 can wrap its three bound methods in the graph. Model arguments never include
the user identity, database path, SQL or approval decision.

- `tinh_lai_vay(principal, annual_rate_percent, months, method="annuity")` returns
  a monthly schedule and totals. Use `method="declining"` for equal principal with
  declining interest. The nominal monthly rate is annual percentage / 1200;
  annuity payment is `P*r/(1-(1+r)^(-n))` (or `P/n` at zero rate).
  Principal must be 0.01 through 10^15 with at most two decimal places, annual
  percentage 0 through 100, and months an integer from 1 through 600. Money uses
  Decimal arithmetic, HALF_UP rounding to two decimals each month, and JSON string
  amounts; the final installment clears rounding residue. Fees and day-count
  conventions are excluded. For example, 1000 at 12% over two annuity months gives
  payments 507.51 and 507.51, interest 15.02, total 1015.02. The returned
  `annual_rate_percent` is canonical text (`"1E+1"` -> `"10"`, `"-0"` -> `"0"`).
- `tra_cuu_giao_dich(account_id=None, limit=20)` uses the read-only store and the
  bound user, masks every returned string, and fails closed if masking fails.
  JSON `\uXXXX` escapes are decoded before masking, so an escaped phone number in
  a JSON description is masked too (escapes JSON requires stay, keeping JSON valid).
  A foreign account returns an empty list even for approver/service roles.
- `tao_ticket(summary)` returns only a masked proposal (same JSON-escape
  masking) with status `pending` and never opens a database. Its masked `created_by` is a display field. The graph
  must keep the real owner in trusted authenticated state, interrupt for approval
  and call TicketStore only after resolving a valid decision. Role `approver` does
  not turn a proposal into a write or bypass the no-self-approval rule.

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
The bucket counts authenticated, valid enqueue attempts, including attempts that
later return 503 (queue full, Redis enqueue failure or masking unavailable). These
tokens are not refunded; clients should back off on 503 rather than retry rapidly.
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
The Compose worker has no API-key registry or audit volume mounts. Its healthcheck
checks its own Redis registration and last heartbeat, allowing RQ's default idle
dequeue interval (up to 480s including grace). Redis outages fail the check. A hung
parent is detected after that heartbeat window; job hangs are bounded by the job
timeout. Docker marks failed checks unhealthy; `restart: unless-stopped` restarts
exited processes and does not automatically restart an unhealthy running process.
After an abrupt kill (SIGKILL/OOM), an old registration can share the restarted
container's hostname and PID 1. The check can report healthy from that registration
for up to about 480s, even if the replacement worker hangs or fails to register.
Before using this healthcheck for autoheal or orchestrator recovery, require the
registration's birth time to be after the current process's start time (for
example, from `/proc/1/stat` or a startup timestamp recorded by the worker).

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
