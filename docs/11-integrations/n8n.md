---
id: n8n-integration
title: n8n Integration
type: reference
domain: integrations
module: n8n
tags: [n8n, workflow, automation]
priority: 3
---
# n8n Integration (FR-08, owner B; classification prompt owner A)

Workflows exported to `infrastructure/n8n/workflows/`:
1. `intake-to-reply.json` — Form/Email trigger → classify (`/chat`) → `/ask/jobs` + poll with Wait → approval (Send and Wait) → reply via Mailpit.
2. `error-handler.json` — Error Trigger → notify operator.

n8n authenticates with a dedicated service API key (department `public`). Webhooks use the production URL.
