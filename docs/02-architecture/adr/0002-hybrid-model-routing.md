---
id: adr-0002-hybrid-model-routing
title: ADR 0002 — Hybrid local and cloud model routing
type: reference
domain: architecture
module: routing
tags: [adr, routing, llm, t-043]
priority: 2
---
# ADR 0002 — Hybrid local and cloud model routing

- **Date**: `2026-11-06`
- **Owner**: `trong-hung`
- **Status**: `Retrospective implemented-design record; reviewed in T-043 (claude-review-b, APPROVED)`
- **Authority**: Existing sensitive-routing requirements and approved CR-008 provider migration.

## Context

The MVP needs cloud quality for eligible questions while retaining sensitive text
and confidential contexts on local inference. Masking alone is not permission to
route an originally sensitive request to the cloud.

## Decision

`decide_route` selects `local-chat` for detected PII, `force_local`, confidential
or unknown classifications; otherwise public/internal chunks are eligible for
`cloud-chat`. Retain sensitive agent history and recognize legacy queue PII
placeholders. Mask before model calls, checkpoints, backend logs/traces and queue
persistence; fail closed when masking fails.

All inference goes through `app/llm.py` and authenticated LiteLLM. The cloud alias
uses the configured OpenAI model; local aliases use Ollama qwen2.5:3b and optional
7b. In Compose only LiteLLM receives the provider key; API/worker use a separate
gateway key. Gateway config has no cross-provider fallback. Missing local inference
returns a sanitized dependency error rather than silently sending data to OpenAI.

Full evaluation similarly uses a local judge for local-routed answers; current
faithfulness judging takes the median of three judgments. Existing saved T-038
scores predate that median change and are labelled accordingly.

## Consequences and alternatives

- Cloud-only routing would not satisfy the local-sensitive policy. Local-only
  avoids provider calls but the CPU model has measured latency/answer-quality limits.
- Gateway liveness is not model readiness; explicitly pull weights and smoke-test
  both aliases before a demo. Local cold starts must stay outside the timed script.
- Previously measured `/ask` p95 is 8.746s cloud, 21.899s local and 19.185s combined.
  Route-separated reporting is an existing owner decision, not a new T-043 waiver.
- `internal` classification can be cloud-eligible under current policy; RBAC still
  applies independently. A supplied unknown/misspelled classification routes local;
  missing required index fields are invalid data, not a grant of extra access.

## Evidence

- [Routing](../../../src/app/routing.py), [LLM client](../../../src/app/llm.py), [gateway aliases](../../../infrastructure/litellm/config.yaml).
- [API routing tests](../../../tests/api/test_ask_routing.py), [sensitive-history graph tests](../../../tests/unit/test_agent_graph.py).
- [CR-008](../../../.agent/governance/change-requests/CR-008.md), [quality/latency notes](../../12-ai/rag-eval-notes.md).
