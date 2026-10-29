---
id: ai-design
title: AI Design
type: reference
domain: ai
module: rag
tags: [ai, rag, llm, prompt]
priority: 1
---
# Thiết kế AI (owner A)

## Model
| Mục đích | Model | Qua |
|---|---|---|
| Embedding | `BAAI/bge-m3` dense + sparse (CPU) | local |
| Rerank | `BAAI/bge-reranker-v2-m3` (CrossEncoder; điểm đã qua sigmoid) | local |
| Chat (cloud) | alias `cloud-chat` → `openai/<OPENAI_MODEL>` | LiteLLM |
| Chat (local) | alias `local-chat` → `ollama_chat/qwen2.5:3b` (`local-chat-7b` tuỳ chọn) | LiteLLM |
| Judge | `JUDGE_MODEL` (mặc định = `OPENAI_MODEL`) | RAGAS |

## Các mode retrieval
`dense`, `hybrid` (RRF của dense + sparse), `hybrid_rerank` (mặc định). `REFUSAL_THRESHOLD` áp lên điểm rerank; dưới ngưỡng → từ chối.

## Prompt
`src/app/prompts.py`: `SYSTEM`, `build_context()`, `CANARY`, `PROMPT_VERSION`. Chỉ trả lời dựa trên ngữ cảnh đã đánh số, trích `[n]`, nếu không thì trả `REFUSAL`.

## Đánh giá
Các trường của `eval/golden.jsonl`: `user_input, reference, sources[{file,page}], category, difficulty, in_scope`. Báo cáo: `docs/12-ai/rag-eval-report.md`.

## Cloud provider selection (CR-008)

Default OPENAI_MODEL is `gpt-6-luna`, the current economical successor to deprecated GPT-4o mini. It supports Chat Completions and structured outputs. Standard text pricing checked 2026-10-29: USD 0.10 / 1M input tokens and USD 0.50 / 1M output tokens for prompts up to 272K input tokens; longer prompts have higher rates. This preserves the low-cost model role in CR-008. Source: https://developers.openai.com/api/docs/models/gpt-6-luna . Judge calls use LiteLLM; JUDGE_MODEL defaults to OPENAI_MODEL at the future eval adapter (T-023), not a direct provider key in eval.
