---
id: llm-client-development
title: LLM gateway client
type: reference
domain: platform
module: src/app/llm.py
tags: [llm, gateway, development]
priority: 2
---
# LLM gateway client

The synchronous client implements the existing LLM contract:

```python
from app.llm import chat

result = chat([{"role": "user", "content": "Reply pong"}], "cloud-chat", temperature=0.0)
print(result.text, result.model, result.input_tokens, result.output_tokens)
```

Default `LLM_BACKEND=fake` returns a deterministic answer without network access.
Set `LLM_BACKEND=litellm`, `LLM_BASE_URL=http://127.0.0.1:4000` and
`LITELLM_MASTER_KEY` to use the gateway. The URL may include `/v1`.
Inside Compose, use `http://litellm:4000`. Only the gateway needs the provider key.
Environment settings are read on each call; the client does not load `.env.local`.

Choose `cloud-chat`, `local-chat` or `local-chat-7b`. The client sends
`reasoning_effort=none` for the configured cloud reasoning model so
that the requested temperature is accepted, matching the gateway smoke tool.
It preserves the alias on every retry and never changes providers.
It makes at most three attempts for
429/5xx, with 0.5 and 1 second delays and a 30 second HTTP timeout per attempt.
Transport failures and other HTTP errors fail immediately with `app.llm.LLMError`.
Error messages omit response bodies and request contents. Missing usage fields
produce zero token counts. Malformed completions fail explicitly.

Verify locally with `python -m pytest tests/unit/test_llm.py -q`.
With Docker running, verify the actual client through LiteLLM and a synthetic
provider using `python -m pytest tests/integration/test_gateway_openai.py -m integration -q`.
The controlled integration test does not need a real provider key.
