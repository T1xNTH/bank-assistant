---
id: rerank-development
title: Reranking and the refusal threshold
type: reference
domain: rag
module: src/app/rag/rerank.py
tags: [rerank, refusal, t-017, e-004]
priority: 2
---
# Rerank và ngưỡng từ chối

`rerank(question, hits, k)` chấm từng cặp (câu hỏi, nội dung chunk) bằng cross-encoder `BAAI/bge-reranker-v2-m3`. Điểm đi qua sigmoid nên nằm trong (0, 1). Hàm trả về tối đa `k` hit có điểm từ ngưỡng trở lên, xếp từ cao xuống thấp, và `Hit.score` là điểm rerank. Danh sách rỗng nghĩa là không tìm thấy gì đủ liên quan: answerer (T-018) trả lời `REFUSAL`. Model chạy trên CPU (fp32) qua `transformers` (tokenizer + đầu phân loại, đã có sẵn do FlagEmbedding kéo về), nạp một lần cho mỗi process ở lần gọi đầu, khoảng 2,3 GB. Không dùng `FlagReranker.compute_score`: bản 1.4.2 chấm batch đầu hai lần để dò kích thước batch, làm rerank 5 ứng viên chậm gấp đôi. Điểm của hai cách trùng nhau (sai lệch tối đa 2,5e-7 trên 30 cặp thật).

Mode `hybrid_rerank` của `retrieve()` (mặc định của `RETRIEVAL_MODE`) lấy `RERANK_CANDIDATES` kết quả hybrid (vẫn qua bộ lọc phòng ban và văn bản bị thay thế), rồi giữ `k` kết quả rerank tốt nhất đạt ngưỡng. Vì vậy mode này có thể trả ít hơn `k` kết quả, hoặc không trả kết quả nào.

## Cấu hình

- `REFUSAL_THRESHOLD`: số trong [0, 1]; để trống thì dùng 0,5. Giá trị sai (chữ, âm, lớn hơn 1, `nan`) báo `ValueError`, không âm thầm dùng mặc định.
- `RERANK_CANDIDATES`: số nguyên từ 1 đến 100; để trống thì dùng 5. Giá trị sai báo `ValueError`.

## Vì sao 5 ứng viên và ngưỡng 0,5

Đo trên `bank_docs` (30 tài liệu, 2.815 chunk) ngày 2026-10-30, máy CPU 16 nhân, model đã nạp sẵn, 12 câu hỏi mẫu trong phạm vi và các câu ngoài phạm vi:

| Ứng viên | Rerank (trung vị / tối đa) | Câu trong phạm vi tìm được | Điểm cao nhất của câu ngoài phạm vi |
|---|---|---|---|
| 20 | 11,3 s / 14,9 s | 12/12 | 0,50 |
| 10 | 5,7 s / 8,1 s | 12/12 | 0,50 |
| 5 | 1,9 s / 3,7 s | 12/12 | 0,34 |

(26 câu, chấm một lần mỗi batch. Bản đầu dùng `FlagReranker.compute_score` đo được 4,0 s / 9,1 s / 12,2 s vì chấm lặp.) NFR-08 cho cả `/ask` dưới 10 giây, gồm cả embed, Qdrant và LLM. Owner trong-hung chọn 5 ứng viên. Lượng tử hóa int8 làm điểm lệch đi (câu ngoài phạm vi lên 0,54), nên không dùng. Giảm `max_length` xuống 512 không nhanh hơn, vì cặp dài nhất chỉ 418 token.

Với 5 ứng viên, điểm cao nhất của câu trong phạm vi thấp nhất là 0,74 ("Phí chuyển tiền ra nước ngoài"), của câu ngoài phạm vi cao nhất là 0,34 ("Ngân hàng Nhà nước có bao nhiêu chi nhánh?"). Ngưỡng 0,5 nằm giữa hai mức đó. Câu thời tiết, bóng đá, nấu ăn chỉ được dưới 0,01. Câu về ngân hàng khác hay dữ liệu trực tiếp (giá vàng, tỷ giá) được dưới 0,06. Đây là mẫu nhỏ, cùng bộ câu đã dùng để chọn ngưỡng. Review độc lập thử thêm câu ngoài mẫu và thấy biên hẹp hơn: "Vay mua nhà trả góp cần hồ sơ gì?" (user credit) chỉ được 0,364 nên bị từ chối dù TT 39 trả lời được; "mất thẻ ATM" (credit) được 0,532. Ngưỡng cần đo lại trên 50 câu của E-008.

## Kiểm thử

- `pytest tests/unit/test_rerank.py`: cross-encoder giả. Kiểm tra thứ tự, điểm, ngưỡng (mặc định, từ env, giá trị sai), câu ngoài phạm vi trả rỗng, nạp model một lần, và `hybrid_rerank` lấy đúng số ứng viên.
- `pytest -m integration tests/integration/test_rerank_refusal.py`: model thật trên collection đã ingest. 12 câu trong phạm vi giữ đúng tài liệu (cho phép trượt 1), 14 câu ngoài phạm vi không trả kết quả nào. Mất khoảng 2 phút.
