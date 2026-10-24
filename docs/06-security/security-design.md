---
id: security-design
title: Security Design
type: reference
domain: security
module: security
tags: [security, pii, rbac, auth]
priority: 1
---
# Security Design

## Threats in scope (OWASP LLM Top 10 subset)
Prompt injection (LLM01), sensitive information disclosure (LLM02), excessive agency (LLM06), system prompt leakage (LLM07).

## Controls
| Control | Implementation | Owner | Test |
|---|---|---|---|
| Authentication | `X-API-Key`, SHA-256 hashed in `config/api_keys.json`; real keys only in `.env.local` | B | 401 tests |
| RBAC | Qdrant filter `department ∈ {user, public}` inside the query | A (filter) / B (User) | cross-department leakage tests |
| PII masking | Presidio regex recognizers + VN patterns (CCCD 12 digits, account numbers, VN phone) on input, output, log, trace, queue | B | log/trace scan tests |
| Sensitive routing | PII or `confidential` chunk → local model | A | routing tests |
| Excessive agency | `tao_ticket` behind `interrupt`; only role `approver` may decide; DB read-only for lookup | A / B | HITL tests |
| Prompt injection | system prompt with canary, context delimiting, refusal policy; ≥ 10 injection tests | A | `tests/security/` |
| Audit | every request logged (masked) with trace id | B | audit tests |
| Supply chain | trivy image scan in CI | B | CI |

## Out of scope for MVP
SSO/OIDC, secret manager, TLS, pentest (see SRS exclusions).
