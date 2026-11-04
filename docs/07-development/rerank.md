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

`rerank(question, hits, k)` chấm từng cặp (câu hỏi, nội dung chunk) bằng cross-encoder `BAAI/bge-reranker-v2-m3`. Điểm đi qua sigmoid nên nằm trong (0, 1). Hàm trả về tối đa `k` hit có điểm từ ngưỡng trở lên, xếp từ cao xuống thấp, và `Hit.score` là điểm rerank. Danh sách rỗng nghĩa là không tìm thấy gì đủ liên quan: answerer (T-018) trả lời `REFUSAL`. Model chạy trên CPU (fp32) qua `transformers` (tokenizer + đầu phân loại, đã có sẵn do FlagEmbedding kéo về), nạp một lần cho mỗi process ở lần gọi đầu, khoảng 2,3 GB. Không dùng `FlagReranker.compute_score`: bản 1.4.2 chấm batch đầu hai lần để dò kích thước batch, làm rerank 5 ứng viên chậm gấp đôi. Như FlagReranker, câu hỏi dài hơn 768 token (3/4 `MAX_LENGTH`) bị cắt trước khi ghép cặp; chỉ cắt phần chunk thì lỗi khi riêng câu hỏi đã vượt 1024 token (2.000 ký tự emoji hay dấu câu, mức tối đa `/ask` nhận). Điểm của hai cách trùng nhau: sai lệch tối đa 2,7e-7 trên 31 cặp thật, kể cả câu hỏi 2.000 ký tự và đoạn văn 3.800 token.

Mode `hybrid_rerank` của `retrieve()` (mặc định của `RETRIEVAL_MODE`) lấy `RERANK_CANDIDATES` kết quả hybrid (vẫn qua bộ lọc phòng ban và văn bản bị thay thế), rồi giữ `k` kết quả rerank tốt nhất đạt ngưỡng. Vì vậy mode này có thể trả ít hơn `k` kết quả, hoặc không trả kết quả nào.

## Cấu hình

- `REFUSAL_THRESHOLD`: số trong [0, 1]; để trống thì dùng 0,5. Giá trị sai (chữ, âm, lớn hơn 1, `nan`) báo `ValueError`, không âm thầm dùng mặc định.
- `RERANK_CANDIDATES`: số nguyên từ 1 đến 100; để trống thì dùng 8 (T-038; trước đó 5). Giá trị sai báo `ValueError`.

## Vì sao ngưỡng 0,5 (và 5 ứng viên trước T-038)

Đo trên `bank_docs` (30 tài liệu, 2.815 chunk) ngày 2026-10-30, máy CPU 16 nhân, model đã nạp sẵn, 12 câu hỏi mẫu trong phạm vi và các câu ngoài phạm vi:

| Ứng viên | Rerank (trung vị / tối đa) | Câu trong phạm vi tìm được | Điểm cao nhất của câu ngoài phạm vi |
|---|---|---|---|
| 20 | 11,3 s / 14,9 s | 12/12 | 0,50 |
| 10 | 5,7 s / 8,1 s | 12/12 | 0,50 |
| 5 | 1,9 s / 3,7 s | 12/12 | 0,34 |

(26 câu, chấm một lần mỗi batch. Bản đầu dùng `FlagReranker.compute_score` đo được 4,0 s / 9,1 s / 12,2 s vì chấm lặp.) NFR-08 cho cả `/ask` dưới 10 giây, gồm cả embed, Qdrant và LLM. Owner trong-hung chọn 5 ứng viên. Lượng tử hóa int8 làm điểm lệch đi (câu ngoài phạm vi lên 0,54), nên không dùng. Giảm `max_length` xuống 512 không nhanh hơn, vì cặp dài nhất chỉ 418 token.

Với 5 ứng viên, điểm cao nhất của câu trong phạm vi thấp nhất là 0,74 ("Phí chuyển tiền ra nước ngoài"), của câu ngoài phạm vi cao nhất là 0,34 ("Ngân hàng Nhà nước có bao nhiêu chi nhánh?"). Ngưỡng 0,5 nằm giữa hai mức đó. Câu thời tiết, bóng đá, nấu ăn chỉ được dưới 0,01. Câu về ngân hàng khác hay dữ liệu trực tiếp (giá vàng, tỷ giá) được dưới 0,06. Đây là mẫu nhỏ, cùng bộ câu đã dùng để chọn ngưỡng. Review độc lập thử thêm câu ngoài mẫu và thấy biên hẹp hơn: "Vay mua nhà trả góp cần hồ sơ gì?" (user credit) chỉ được 0,364 nên bị từ chối dù TT 39 trả lời được; "mất thẻ ATM" (credit) được 0,532. Ngưỡng cần đo lại trên 50 câu của E-008.

## Đo lại trong T-038: 8 ứng viên

Đo trên 50 câu golden (40 câu trong phạm vi, user theo phòng ban của tài liệu vàng), collection ingest bằng chunker T-038, fp32, máy rảnh (không chạy model local cùng lúc), ngày 2026-11-04. Thời gian là riêng bước rerank.

| Ứng viên | hit@5 | Rerank p50 / p95 | Câu trong phạm vi có điểm cao nhất < 0,5 |
|---|---|---|---|
| 5 | 0,90 | 2,3 s / 3,3 s | 1 |
| 7 | 0,90 | 3,6 s / 5,2 s | 1 |
| 8 | 0,925 | 4,2 s / 6,2 s | 1 |
| 10 | 0,95 | 4,9 s / 7,4 s | 0 |

Chunk đúng của hai câu bảng phí đứng hạng 8 và 13–16 sau `hybrid`, nên 5 ứng viên không bao giờ tới được. Chọn 8: hai mức cao hơn vẫn tăng hit@5, nhưng 10 ứng viên cộng embed và LLM đưa p95 `/ask` sát 10 giây (NFR-08). Mỗi ứng viên tốn khoảng 0,6–0,7 s trên CPU này. Đã thử và bỏ: int8 (`quantize_dynamic`) nhanh gấp 2,2 lần nhưng hit@5 còn 0,875 ở 10 ứng viên; cắt chunk ở 384 token không nhanh hơn (chunk đã ngắn hơn), ở 256 token thì hit@5 còn 0,90. Câu ngoài phạm vi có điểm cao nhất 0,968 ở mọi mức là một câu mà LLM vẫn từ chối (NFR-03 = 1,0 trong eval). Ngưỡng 0,5 giữ nguyên.

## Kiểm thử

- `pytest tests/unit/test_rerank.py`: cross-encoder giả; hàm chấm thật được kiểm với tokenizer và model giả (sigmoid, batch theo thứ tự, tham số cắt, câu hỏi dài). Kiểm tra thứ tự, điểm, ngưỡng (mặc định, từ env, giá trị sai), câu ngoài phạm vi trả rỗng, nạp model một lần, và `hybrid_rerank` lấy đúng số ứng viên.
- `pytest -m integration tests/integration/test_rerank_refusal.py`: model thật trên collection đã ingest. 12 câu trong phạm vi giữ đúng tài liệu (cho phép trượt 1), 14 câu ngoài phạm vi không trả kết quả nào; câu hỏi dài đúng giới hạn của API vẫn được chấm. Mất khoảng 2 phút.
