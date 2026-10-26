---
id: observability-design
title: Observability Design
type: reference
domain: observability
module: tracing
tags: [observability, langfuse, cost]
priority: 2
---
# Thiết kế observability (FR-10, owner B)

Langfuse tự host (compose profile `obs`), ghim phiên bản `<5` cho Python 3.10. Input được che trước khi ghi trace (`capture_input=False` + input đã che).

| Chỉ số | Nguồn |
|---|---|
| Latency p50/p95 theo endpoint | thời lượng trace |
| Thời gian chờ trong hàng vs thời gian xử lý | timestamp của các span trong job |
| Token và chi phí theo request / theo ngày | `llm_cost.cost_of()` |
| Tỉ lệ từ chối | tag `found=false` |
| Feedback 👍/👎 | `POST /feedback` → score trong Langfuse |
