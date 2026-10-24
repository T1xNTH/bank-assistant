# Contributing

Read `docs/07-development/team-workflow.md` (Vietnamese) first. Short version:

1. Pick a `pending` task you own from `.agent/execution/task-board.md`; `scripts/agent task start T-xxx`.
2. Branch `feat/T-xxx-<slug>`, TDD, keep the PR under ~400 lines.
3. `scripts/agent task report|verify ...`, then get an independent review from a **separate** Claude Code session.
4. Open a PR using the template; the other owner approves; squash merge; `scripts/agent task done T-xxx`.
5. Contract changes (`docs/04-api/openapi.yaml`, `src/app/contracts.py`) need a `contract` PR, a change request, and both owners.
