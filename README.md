# bank-assistant

Internal assistant for bank staff: answers **only from internal documents** with file/page citations, refuses when the answer is not there, enforces department permissions, masks personal data, and runs a small agent (loan calculation, transaction lookup, ticket creation with human approval). API-first, integrated with n8n.

> Status: MVP implementation, with release QA tracked in T-041. See the
> [v1.0-mvp release QA report](.agent/reports/releases/RELEASE-v1.0-mvp.md)
> for requirement evidence, known limits and release readiness.

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
to rerun setup. Seeding is an explicit first-run step before using the transaction
tool in Docker; restarting containers preserves the database. Fake authentication
uses user `dev`, which has no seeded transactions. For transaction demos, generate
the synthetic-user API key above, set `AUTH_BACKEND=apikey` in `.env.local`, and run
`make up` again so the API reads the updated environment. Use that key in
`X-API-Key`. Tool selection also needs a configured real LLM; the generic fake LLM
does not select agent tools.

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

## Agent graph (T-030)

`AgentService` in `app.agent.graph` is what the `/agent` endpoints (T-031) call:

- `run(user, message, thread_id=None)` masks the message (fail-closed), lets the
  model pick one tool as JSON through `app.llm` (alias from `decide_route`: local
  when the thread had PII or customer transactions), runs it with `ToolNode`, and
  returns `AgentResult(thread_id, status, answer, pending_action)`. Document
  questions go to RAG and keep `[n]` plus a source list; loan and transaction
  replies are written by code, because masking turns 8+ digit amounts into
  `<ACCOUNT_NUMBER>`. Accounts appear as `TK1`, `TK2`, ...
- Amounts typed as digits (`100.000.000 đ`) are masked with numbered
  placeholders (`<ACCOUNT_NUMBER_1>`); the model passes the placeholder as
  `principal` and the tool reads the real value from memory for that call only
  (never the checkpoint, never the model). Such a message counts as PII, so the
  thread routes to `local-chat`. A rate or term that no user message states is
  asked for instead of computed.
- `AgentResult.answer_source`: `"tool"` = written by code from tool results
  whose text is already masked; the API returns it unmasked (masking again
  would hide the amounts). `"model"` = mask as usual. Logs and audit mask both.
- `tao_ticket` stops at `interrupt` with status `pending_approval`; nothing is
  written. `decide(thread_id, approver, approve, comment=None)` resumes it; only
  role `approver`, never the owner, and only once (`DecisionConflict` after that).
  The ticket owner is the authenticated user stored in the thread.
- Threads live in the SQLite checkpointer at `AGENT_CHECKPOINT_DB_PATH`
  (masked text only) and survive restarts. Errors for T-031: `ThreadNotFound`
  404 (also for another user's thread), `PermissionError` 403,
  `DecisionConflict` 409, `AgentUnavailable` 503. The HTTP adapter maps invalid
  input (`ValueError`) to 400, as specified by the public API contract.

`POST /agent` accepts `{"message":"...","thread_id":null}`; omit `thread_id`
to start a thread, or send the returned ID to continue one owned by the caller.
It returns `{thread_id, status, answer, pending_action}`; `status` is `completed`
or `pending_approval`. With a pending ticket, a different authenticated user with
role `approver` calls `POST /agent/{thread_id}/decision` with
`{"approve":true,"comment":"..."}` (or `false` to reject). `approve` must be a
JSON boolean. Staff/service users and self-approval receive 403, unknown/other
users' threads receive 404 on continuation, and repeating a decision receives 409.
Approvers may decide across departments, matching the current role-only policy.

The app shares one `AgentService` across requests so its locks and amount vault
work across turns. Use one API worker; multiple worker processes would need a
shared approval lock. The SQLite connection closes on app shutdown. Checkpoints
survive restarts; the in-memory amount vault does not, so the agent asks for an
amount again when needed. The existing `CORE_BANKING_DB_PATH`, `TICKETS_DB_PATH`
and `AGENT_CHECKPOINT_DB_PATH` settings select storage; seed synthetic banking
data with `scripts/seed_core_banking.py` before using the transaction tool.

Agent messages are masked inside the trusted service before checkpoints/model
calls, while audit records store masked messages and decision bodies (including
the approver's authenticated identity). Free model replies and pending summaries
are masked at HTTP egress; code-rendered loan/transaction replies keep numeric
amounts and already-masked text. `answer_source` is internal and is not returned.
Do not automatically repeat a ticket proposal after a 503: a ticket write and its
checkpoint/audit live in separate transactions, so a storage failure can leave a
committed ticket despite the failed HTTP response. Reconcile the existing ticket
before creating a replacement.

## Quick start

Run from Bash on Linux or WSL with Git, Python 3, GNU Make, curl and Docker Engine
with Compose v2 available. Docker needs enough disk for the Python/ML image;
the first build downloads its dependencies. Ports 8000, 6333, 6379 and 4000 must
be available on loopback. Existing projects can keep their volumes: use a fresh
`COMPOSE_PROJECT_NAME` for an isolated demo, and stop a project occupying these
ports before starting another one.

The default configuration runs fake RAG/LLM/authentication and real API, Redis,
worker, Qdrant and gateway containers. It needs no provider key, corpus snapshot,
model download or host Python packages. Create a private local gateway key first:

```bash
git clone https://github.com/T1xNTH/bank-assistant.git
cd bank-assistant
cp .env.example .env.local
python3 - <<'PY'
from pathlib import Path
import secrets
path = Path(".env.local")
path.write_text(path.read_text().replace(
    "LITELLM_MASTER_KEY=\n",
    "LITELLM_MASTER_KEY=sk-" + secrets.token_hex(32) + "\n",
))
PY
make up
make smoke
docker compose -f infrastructure/compose.yaml --env-file .env.local exec -T api \
  python - < scripts/smoke_api.py
```

`make up` waits for all five core services to be healthy. `make smoke` checks API,
Qdrant and Redis; the final command exercises a cited fake answer, out-of-scope
refusal, error envelopes and request IDs over HTTP. `/ask` returns a canned answer
in this mode; these checks establish startup and wiring, not real RAG quality.
Optional profiles, real-model configuration and synthetic banking setup are
documented below and above. `make down` stops the core stack while keeping data.

For host-side development and the full test suite, install the development
dependencies separately:

```bash
make setup                      # .venv + dev/UI dependencies
make check                      # Ruff + pytest + framework validation
```

The running API and worker share Redis, required even with fake backends. To run
the API directly on the host, first stop the Compose API to free port 8000, load
`.env.local` into the shell (`set -a; . ./.env.local; set +a`), then use
`.venv/bin/uvicorn app.main:app --app-dir src --port 8000`. Keep Redis running.

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

`POST /ask`, `POST /chat` and `POST /ask/jobs` share one Redis token bucket per
authenticated API-key digest:
`API_KEY_RPM` (default 60) and `API_KEY_BURST` (default 10). Exhaustion returns the
standard 429 envelope with integer `Retry-After`; polling is not throttled.
All three endpoints require Redis even with fake LLM/RAG backends. If Redis is
unavailable, they fail closed with 503 before calling a backend or enqueueing;
check `REDIS_URL` and Redis health before retrying.
The bucket counts authenticated attempts, including requests with invalid bodies
and attempts that later return 503 (queue full, Redis enqueue failure or masking
unavailable). These
tokens are not refunded; clients should back off on 503 rather than retry rapidly.
With `AUTH_BACKEND=fake` and no `X-API-Key`, requests share the fake user `dev`'s
bucket across these endpoints. Rapid UI demo clicks can exhaust the default burst
of 10 and return 429; wait for refill or increase `API_KEY_BURST` for the demo.
`POST /agent` and `POST /agent/{thread_id}/decision` currently have no API token
bucket; extending the shared limiter is tracked as a follow-up in
[the T-037 review report](.agent/reports/review/T-037.md#findings).
Worker execution attempts share one Redis bucket (`WORKER_RPM`, default 60,
capacity 1), including retries. The LLM
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

## Compose profiles and Qdrant recovery (T-040)

With Docker Compose v2 and Bash/WSL, copy `.env.example` to `.env.local` and set
`LITELLM_MASTER_KEY` to a random `sk-` prefixed value. Core services start with
`make up`; fake backends need no provider key. Each optional profile works with
core services without enabling either other profile:

| Command | Additional services |
|---|---|
| `make up PROFILE=local-llm` | Ollama on 11434 (pull a model separately before local inference) |
| `make up PROFILE=automation` | n8n on 5678, Mailpit UI on 8025 / SMTP on 1025 |
| `make up PROFILE=obs` | Langfuse on 3000, worker, PostgreSQL, ClickHouse, MinIO, Redis |

Equivalent: `docker compose -f infrastructure/compose.yaml --env-file .env.local
--profile <profile> up -d --build --wait --wait-timeout 600` (one shell line).
Startup waits up to 600 seconds (`COMPOSE_WAIT_TIMEOUT` overrides it).
All published ports bind to loopback. `make down PROFILE=<profile>` stops that
profile and core while preserving volumes; `make logs PROFILE=<profile>` follows logs.
Tracing setup is in the observability guide below.

Stop ingestion and all writers before backing up a collection. Counts before/after
detect count changes, but cannot detect an equal-count update. The snapshot includes
vectors, payloads, indexes and collection configuration, not other application stores.

```bash
make backup QDRANT_COLLECTION=bank_docs
# On a recovery instance where bank_docs does not exist:
make restore QDRANT_COLLECTION=bank_docs
```

Both commands use the host Python environment and `httpx2` from `make setup`.
`QDRANT_URL` defaults to `http://127.0.0.1:6333`; `BACKUP_DIR` defaults to
`data/backups/qdrant`. Export `QDRANT_API_KEY` when the server requires it.
The tools do not read `.env.local`: pass Make variables or export these settings.
Use a separate `BACKUP_DIR` for each collection and serialize backup/restore jobs.
`backup.json` points to the most recently completed local snapshot and records its
SHA-256 and exact point count. Copy the entire backup directory to durable storage;
older snapshot files may be retained for recovery. Failed downloads never replace
the prior manifest. Server-side snapshots are removed after download.

Restore validates the checksum and collection name before uploading and verifies
the exact count afterwards. It refuses to overwrite an existing collection. For a
backup → delete → restore drill, use a disposable collection and explicitly delete
only that collection between the commands. A failed restore may leave a collection
behind; inspect it before retrying. Keep writers paused until count verification
passes. Use the same pinned Qdrant v1.12.4 for recovery.

With Qdrant running, `python scripts/smoke_qdrant_backup.py` exercises the actual
Make targets using a uniquely named synthetic collection, then removes only that
collection. The `Compose and Qdrant recovery` workflow runs `make check`, starts
each complete profile independently and repeats this recovery drill on Linux.
It runs for infrastructure pull requests and also supports manual dispatch.

## Optional tracing (T-035)

Enable the Compose `obs` profile for local Langfuse. Without both Langfuse API keys,
tracing stays off. Enabled `/ask` and job responses use the exported trace's actual
ID; masked request/output data and retrieve/rerank/LLM timing appear in Langfuse.
Worker traces separate queue waiting from processing. See the
[setup, timing definitions and verification](docs/13-observability/observability.md).

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
