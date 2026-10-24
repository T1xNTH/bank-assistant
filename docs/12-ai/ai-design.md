---
id: ai-design
title: AI Design
type: reference
domain: ai
module: rag
tags: [ai, rag, llm, prompt]
priority: 1
---
# AI Design (owner A)

## Models
| Purpose | Model | Via |
|---|---|---|
| Embedding | `BAAI/bge-m3` dense + sparse (CPU) | local |
| Rerank | `BAAI/bge-reranker-v2-m3` (CrossEncoder; scores already sigmoid) | local |
| Chat (cloud) | alias `cloud-chat` → `gemini/<GEMINI_MODEL>` | LiteLLM |
| Chat (local) | alias `local-chat` → `ollama_chat/qwen2.5:3b` (`local-chat-7b` optional) | LiteLLM |
| Judge | `JUDGE_MODEL` (default = `GEMINI_MODEL`) | RAGAS |

## Retrieval modes
`dense`, `hybrid` (RRF of dense + sparse), `hybrid_rerank` (default). `REFUSAL_THRESHOLD` on rerank score; below → refusal.

## Prompt
`src/app/prompts.py`: `SYSTEM`, `build_context()`, `CANARY`, `PROMPT_VERSION`. Answer only from numbered context, cite `[n]`, otherwise return `REFUSAL`.

## Evaluation
`eval/golden.jsonl` fields: `user_input, reference, sources[{file,page}], category, difficulty, in_scope`. Report: `docs/12-ai/rag-eval-report.md`.
