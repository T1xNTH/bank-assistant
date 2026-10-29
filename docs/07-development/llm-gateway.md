---
id: llm-gateway-setup
title: LiteLLM and Ollama development setup
type: reference
domain: development
module: infrastructure
tags: [litellm, ollama, t-011]
priority: 2
---
# LLM gateway

Run from the repository root with Docker (on Windows, use WSL).
Copy `.env.example` to `.env.local` and set `GEMINI_API_KEY`, `GEMINI_MODEL`
(bare model ID, default `gemini-flash-latest`) and a random
`LITELLM_MASTER_KEY` beginning with `sk-` (required by Compose).
Generate one with `python3 -c "import secrets; print('sk-'+secrets.token_hex(32))"`.
Only LiteLLM receives the Gemini key.
API receives the gateway key and uses `http://litellm:4000` inside Compose.
All published ports bind to localhost. The gateway requires bearer authentication.

```bash
make up
# Optional local models (CPU supported; allow RAM/disk for the selected size):
docker compose -f infrastructure/compose.yaml --env-file .env.local --profile local-llm up -d --wait
docker compose -f infrastructure/compose.yaml --env-file .env.local exec ollama ollama pull qwen2.5:3b
# Optional larger alias:
docker compose -f infrastructure/compose.yaml --env-file .env.local exec ollama ollama pull qwen2.5:7b
```

LiteLLM remains healthy without a cloud key, Ollama or downloaded weights;
its healthcheck tests gateway liveness, not paid model calls. With the profile
disabled, cloud requests still work and local requests fail without cloud fallback.
Weights persist in `ollama_data`. Pull models explicitly before local smoke checks.

```bash
# Export LITELLM_MASTER_KEY in this shell if configured; this checks host port 4000.
python3 scripts/smoke_llm.py
python3 scripts/smoke_llm.py --models local-chat-7b
# Or use the gateway container's environment/key:
docker compose -f infrastructure/compose.yaml --env-file .env.local exec -T litellm python - < scripts/smoke_llm.py
```

The smoke sends only a synthetic ping and checks for a nonempty answer. Cloud
ping requests use `reasoning_effort=low` and a 2048-token budget so a reasoning
model can produce an answer within the smoke limit. This affects only the smoke.
Cloud checks call Gemini and can consume quota. Errors print status/type without keys
or provider response bodies. CI starts LiteLLM without credentials, and does not
download local weights or make paid model requests. CI generates an ephemeral
gateway key before rendering Compose.

Alias configuration follows the official [LiteLLM config reference](https://docs.litellm.ai/docs/proxy/configs),
[Gemini provider](https://docs.litellm.ai/docs/providers/gemini), and
[Ollama chat provider](https://docs.litellm.ai/docs/providers/ollama).
