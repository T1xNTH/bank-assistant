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
| Chat (cloud) | alias `cloud-chat` → `gemini/<GEMINI_MODEL>` | LiteLLM |
| Chat (local) | alias `local-chat` → `ollama_chat/qwen2.5:3b` (`local-chat-7b` tuỳ chọn) | LiteLLM |
| Judge | `JUDGE_MODEL` (mặc định = `GEMINI_MODEL`) | RAGAS |

## Các mode retrieval
`dense`, `hybrid` (RRF của dense + sparse), `hybrid_rerank` (mặc định). `REFUSAL_THRESHOLD` áp lên điểm rerank; dưới ngưỡng → từ chối.

## Prompt
`src/app/prompts.py`: `SYSTEM`, `build_context()`, `CANARY`, `PROMPT_VERSION`. Chỉ trả lời dựa trên ngữ cảnh đã đánh số, trích `[n]`, nếu không thì trả `REFUSAL`.

## Đánh giá
Các trường của `eval/golden.jsonl`: `user_input, reference, sources[{file,page}], category, difficulty, in_scope`. Báo cáo: `docs/12-ai/rag-eval-report.md`.
