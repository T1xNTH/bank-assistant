---
id: retrieve-development
title: Retrieval modes and access filters
type: reference
domain: rag
module: src/app/rag/retrieve.py
tags: [retrieve, qdrant, rrf, t-016, e-004]
priority: 2
---
# Truy xuất: mode dense và hybrid (RRF)

`retrieve(question, user, k=5, mode="hybrid")` trả về tối đa `k` chunk mà `user` được đọc, theo thứ tự điểm giảm dần. Mỗi kết quả là một `Hit` (`app.contracts`). Câu hỏi được embed một lần bằng bge-m3 (dense + sparse, T-008), rồi truy vấn Qdrant (`QDRANT_URL`, `QDRANT_COLLECTION`, giống `store.py`). Có thể truyền `client` và `collection` để dùng lại kết nối hoặc chạy test.

## Các mode

- `dense`: xếp hạng theo cosine trên vector dense. `score` là cosine.
- `hybrid` (mặc định): Qdrant tự gộp hai danh sách dense và sparse, mỗi danh sách `max(PREFETCH, k)` ứng viên (`PREFETCH = 20`), bằng reciprocal rank fusion (`Fusion.RRF`). `score` là điểm RRF, chỉ dùng để so thứ tự, không so được với cosine.
- `hybrid_rerank`: là `hybrid` rồi đến `rerank.rerank`. Mode này thuộc T-017; hiện tại gọi sẽ báo `NotImplementedError`.

Mode lạ hoặc `k < 1` báo `ValueError`.

## Bộ lọc quyền

Bộ lọc nằm ngay trong truy vấn Qdrant, ở cả mode `dense` lẫn từng nhánh của `hybrid`, chứ không lọc sau khi lấy kết quả (`docs/02-architecture/architecture.md`):
- `department` ∈ {phòng ban của user, `public`}. User `public` chỉ đọc được tài liệu `public`. Phòng ban lạ (không thuộc `Department`) báo `ValueError`.
- `superseded_by` là null: văn bản đã bị thay thế không được trả về. Point không có trường `superseded_by` cũng bị loại.

Vì lọc trong từng nhánh, các chunk bị cấm không chiếm chỗ trong danh sách ứng viên. User `public` vẫn nhận đủ kết quả dù có nhiều chunk `hr` điểm cao hơn.

## Kiểm thử

- `pytest tests/unit/test_retrieve.py`: Qdrant trong bộ nhớ và embedding giả. Kiểm tra thứ tự của từng mode, RRF, bộ lọc theo phòng ban và `superseded_by`, lọc trước khi giới hạn, cùng các tham số sai.
- `pytest -m integration tests/integration/test_retrieve_recall.py`: chạy trên collection đã ingest (`scripts/ingest.py`), bỏ qua nếu collection rỗng. Đo recall@5 của cả hai mode trên 12 câu hỏi mẫu, mỗi câu hỏi do user thuộc phòng ban được đọc tài liệu đó, và kiểm tra bộ lọc trên dữ liệu thật. Đánh giá đầy đủ với 50 câu hỏi nằm ở E-008.
