---
id: observability-design
title: Observability Design
type: reference
domain: observability
module: tracing
tags: [observability, langfuse, cost]
priority: 2
---
# Observability Design (FR-10, owner B)

Langfuse self-hosted (compose profile `obs`), pinned `<5` for Python 3.10. Inputs are masked before tracing (`capture_input=False` + masked input).

| Metric | Source |
|---|---|
| Latency p50/p95 per endpoint | trace duration |
| Queue wait vs processing time | job span timestamps |
| Tokens and cost per request / per day | `llm_cost.cost_of()` |
| Refusal rate | `found=false` tag |
| Feedback 👍/👎 | `POST /feedback` → Langfuse score |
