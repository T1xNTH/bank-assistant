---
id: n8n-integration
title: n8n Integration
type: reference
domain: integrations
module: n8n
tags: [n8n, workflow, automation]
priority: 3
---
# Tích hợp n8n (FR-08, owner B; prompt phân loại do A phụ trách)

Các workflow được export vào `infrastructure/n8n/workflows/`:
1. `intake-to-reply.json` — trigger Form/Email → phân loại (`/chat`) → `/ask/jobs` + poll bằng node Wait → duyệt (Send and Wait) → phản hồi qua Mailpit.
2. `error-handler.json` — Error Trigger → báo cho người vận hành.

n8n xác thực bằng một API key dịch vụ riêng (department `public`). Webhook dùng URL production.
