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

Cần Qdrant có corpus dùng chung (2.819 point sau chunker T-038, xem `corpus.md`), gateway LiteLLM, `LLM_BACKEND=litellm` và `LITELLM_MASTER_KEY` trong môi trường. Thiếu `LLM_BACKEND=litellm` thì runner dừng với lỗi, vì LLM giả trả `"Câu trả lời [1]."` cho mọi câu và mọi chỉ số sẽ trông như đạt:

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
| `faithfulness` | NFR-01 ≥ 0,80 | RAGAS `Faithfulness` trên các câu trong phạm vi được trả lời: câu trả lời so với đúng các chunk đã đưa cho LLM. Judge là `JUDGE_MODEL` (mặc định alias `cloud-chat`) qua LiteLLM, `reasoning_effort="none"` vì RAGAS gửi `top_p`. Câu trả lời đi `local-chat` (có chunk `confidential`, hoặc nhãn lạ/thiếu: fail-closed) **không** được gửi cho judge cloud: nó được chấm bằng `JUDGE_LOCAL_MODEL` (mặc định `local-chat`, bắt buộc là alias `local-*`); nếu không có judge local thì để trống với lý do `not judged: local-only context and no local judge`. Kết quả từng câu ghi thêm `route` và `classification` của từng context (T-027, review PR #93). Câu judge không chấm được (lỗi gọi, hoặc RAGAS trả `nan` khi không tách được mệnh đề nào) thì để trống, ghi lý do vào kết quả và mục "Judge không chấm được" của báo cáo. Faithfulness chỉ được tính là đạt khi judge chấm được ≥ 90% số câu trả lời; giá trị thiếu hoặc `nan` luôn tính là trượt. |
| `hit_at_5` | NFR-02 ≥ 0,75 | Câu trong phạm vi có ít nhất một chunk (trong tối đa 5 chunk đưa cho LLM) trùng `(file, page)` của golden. Với `hybrid_rerank`, chunk dưới ngưỡng rerank đã bị loại, nên câu bị từ chối thì không trúng. |
| `refusal_accuracy` | NFR-03 ≥ 0,90 | Câu ngoài phạm vi có `found: false` và chạy không lỗi. Câu bị lỗi có `found: false` mặc định nhưng không được tính là từ chối đúng. |
| `citation_rate` | NFR-04 = 1,00 | Câu trong phạm vi có `found: true` mang ít nhất một trích dẫn. `RagAnswerer` đổi câu không trích dẫn thành từ chối, nên chỉ số này luôn 1,00 (báo cáo ghi chú điều này); câu bị đổi làm giảm `answer_rate`. |

Ngoài 4 ngưỡng trên, `--check` (và dấu ✅/❌ của báo cáo) còn trượt khi có **câu trích văn bản bị thay thế** (`superseded_cited` > 0, vi phạm FR-02) hoặc **câu vẫn lỗi sau khi thử lại** (`errors` > 0, vì khi đó mọi chỉ số chỉ tính trên một phần lượt chạy). Hai điều kiện này cố định trong code (`MUST_BE_ZERO`), không lấy từ `eval/thresholds.json`.

Ngoài ra báo cáo có: tỉ lệ câu trong phạm vi được trả lời, số lần trích văn bản bị thay thế (phải 0), lỗi và số lần thử lại, độ trễ p50/p95 (nearest-rank; trong process, không gồm HTTP; model được nạp trước khi đo; câu lỗi không tính; câu được thử lại chỉ tính lần cuối), token của LLM trả lời.

**Phòng ban:** mỗi câu được hỏi với user thuộc phòng ban của nguồn không public (nếu có), ngược lại là `public`. Golden không có câu nào cần cả `credit` lẫn `hr`.

**Lỗi tạm thời:** `AnswerUnavailable` (gateway 5xx, timeout, Qdrant khởi động lại) được thử lại tối đa 3 lần, chờ 5, 10 rồi 15 giây. Lỗi kết nối tới gateway ghi rõ loại lỗi (vd `LLM gateway transport failure (ReadTimeout)`) để biết là timeout hay mất kết nối. Lỗi khác không thử lại và được ghi vào kết quả, không làm dừng cả lượt chạy.

## Chi phí và thời gian

Lượt `--all` có judge gồm 150 lượt trả lời và khoảng 120 lượt chấm faithfulness (mỗi lượt vài lời gọi). Với gpt-6-luna (0,10 USD / 1M token vào, 0,50 USD / 1M token ra), chi phí dưới 0,10 USD; số token thực của phần trả lời có trong báo cáo. Thời gian khoảng 15–20 phút trên CPU, chủ yếu cho rerank và các lời gọi LLM.
