---
id: eval-development
title: Running the RAG evaluation
type: reference
domain: ai
module: eval/run.py
tags: [eval, ragas, e-008, t-023]
priority: 2
---
# Chạy đánh giá RAG (`eval/run.py`)

`eval/run.py` hỏi 50 câu của `eval/golden.jsonl` qua `RagAnswerer` (trong process, không qua HTTP) cho từng mode `dense`, `hybrid`, `hybrid_rerank`. Kết quả được chấm theo các ngưỡng NFR trong `eval/thresholds.json`, rồi ghi ra `docs/12-ai/rag-eval-report.md` (sinh tự động) và `eval/results/<mode>.jsonl` (từng câu: câu trả lời, trích dẫn, chunk đã đưa cho LLM, điểm faithfulness, độ trễ, token).

## Cài đặt

RAGAS kéo theo langchain, openai, instructor… nên dùng venv riêng, không cài vào `.venv` chung của app:

```bash
python3 -m venv ~/.venvs/bank-eval
~/.venvs/bank-eval/bin/pip install -r requirements-eval.txt
```

`requirements-eval.txt` ghim `ragas==0.4.3` và langchain < 1 (`langchain-community` 0.4 đã bỏ module `vertexai` mà ragas 0.4.3 vẫn import). Image API và CI không cài các gói này. Unit test của runner (`tests/unit/test_eval_run.py`) dùng judge giả nên chạy được với `.venv` thường.

## Chạy

Cần Qdrant có corpus dùng chung (2.815 point, xem `corpus.md`), gateway LiteLLM, và `LITELLM_MASTER_KEY` trong môi trường:

```bash
export LLM_BACKEND=litellm LITELLM_MASTER_KEY=...   # lấy từ .env.local, đừng in ra
~/.venvs/bank-eval/bin/python eval/run.py --all                       # 3 mode, có judge
~/.venvs/bank-eval/bin/python eval/run.py --mode hybrid_rerank --limit 5   # thử nhanh, rẻ
~/.venvs/bank-eval/bin/python eval/run.py --all --no-judge            # không chấm faithfulness
~/.venvs/bank-eval/bin/python eval/run.py --all --check               # exit 1 nếu trượt ngưỡng (cho CI gate E-015)
```

`--out` và `--results` đổi nơi ghi, dùng khi thử để không ghi đè báo cáo đã commit.

## Các chỉ số

| Chỉ số | NFR | Cách tính |
|---|---|---|
| `faithfulness` | NFR-01 ≥ 0,80 | RAGAS `Faithfulness` trên các câu trong phạm vi được trả lời: câu trả lời so với đúng các chunk đã đưa cho LLM. Judge là `JUDGE_MODEL` (mặc định alias `cloud-chat`) qua LiteLLM, `reasoning_effort="none"` vì RAGAS gửi `top_p`. Câu judge không chấm được thì để trống và đếm riêng. |
| `hit_at_5` | NFR-02 ≥ 0,75 | Câu trong phạm vi có ít nhất một chunk (trong tối đa 5 chunk đưa cho LLM) trùng `(file, page)` của golden. Với `hybrid_rerank`, chunk dưới ngưỡng rerank đã bị loại, nên câu bị từ chối thì không trúng. |
| `refusal_accuracy` | NFR-03 ≥ 0,90 | Câu ngoài phạm vi có `found: false`. |
| `citation_rate` | NFR-04 = 1,00 | Câu trong phạm vi có `found: true` mang ít nhất một trích dẫn. `RagAnswerer` đổi câu không trích dẫn thành từ chối, nên chỉ số này luôn 1,00; tỉ lệ đó hiện ra ở `answer_rate`. |

Ngoài ra báo cáo có: tỉ lệ câu trong phạm vi được trả lời, số lần trích văn bản bị thay thế (phải 0), lỗi và số lần thử lại, độ trễ p50/p95 (trong process, không gồm HTTP), token của LLM trả lời.

**Phòng ban:** mỗi câu được hỏi với user thuộc phòng ban của nguồn không public (nếu có), ngược lại là `public`. Golden không có câu nào cần cả `credit` lẫn `hr`.

**Lỗi tạm thời:** `AnswerUnavailable` (gateway 5xx, timeout, Qdrant khởi động lại) được thử lại tối đa 2 lần. Lỗi khác không thử lại và được ghi vào kết quả, không làm dừng cả lượt chạy.

## Chi phí và thời gian

Lượt `--all` có judge gồm 150 lượt trả lời và khoảng 120 lượt chấm faithfulness (mỗi lượt vài lời gọi). Với gpt-6-luna (0,10 USD / 1M token vào, 0,50 USD / 1M token ra), chi phí dưới 0,10 USD; số token thực của phần trả lời có trong báo cáo. Thời gian khoảng 15–20 phút trên CPU, chủ yếu cho rerank và các lời gọi LLM.
