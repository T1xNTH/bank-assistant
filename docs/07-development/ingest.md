---
id: ingest-development
title: Ingest the corpus into Qdrant
type: reference
domain: rag
module: scripts/ingest.py
tags: [ingest, qdrant, t-010, e-003]
priority: 2
---
# Nạp bộ tài liệu vào Qdrant

`scripts/ingest.py` chạy cả chuỗi E-003 cho từng dòng của `data/manifest.csv`: parse PDF (T-006), chia đoạn (T-007), embed bge-m3 (T-008), rồi ghi vào Qdrant bằng `replace_document` (T-009).

## Chạy

```bash
docker compose -f infrastructure/compose.yaml up -d qdrant     # hoặc make up
.venv/bin/python scripts/ingest.py --data data                  # cả 30 tài liệu
.venv/bin/python scripts/ingest.py --data data --only nd293-2025 # chỉ một vài doc_id
```

Tham số:
- `--data`: thư mục chứa `manifest.csv` và các PDF (mặc định `data`; dựng theo `corpus.md`).
- `--collection`: mặc định `QDRANT_COLLECTION`, không có thì `bank_docs`.
- `--only DOC_ID ...`: chỉ ingest các `doc_id` này. Các tài liệu khác trong collection giữ nguyên.
- `--no-cache`: parse và embed lại từ đầu.

Cần Tesseract (`tooling.md`) và mạng ở lần chạy đầu để tải model của docling và bge-m3. Kết nối Qdrant lấy từ `QDRANT_URL` (mặc định `http://127.0.0.1:6333`) và `QDRANT_API_KEY`.

## Hành vi

- Manifest được kiểm bằng `scripts/check_manifest.py` trước. Có lỗi thì dừng, chưa ghi gì.
- Mỗi tài liệu in một dòng tiến độ (số trang, số chunk, bước nào lấy từ cache, thời gian). Cuối cùng in tóm tắt: số tài liệu thành công, số trang, số chunk, tổng số point trong collection và tổng thời gian.
- Một tài liệu lỗi (ví dụ `ParseError`) được báo và bỏ qua, các tài liệu khác vẫn được ingest. Có tài liệu lỗi thì exit code là 1.
- Payload gồm đủ 9 trường của `docs/05-database/schema.md`: `source`, `page`, `chunk_index`, `text` lấy từ chunk; `doc_id`, `department`, `classification`, `effective_date`, `superseded_by` lấy từ manifest. Ô `superseded_by` để trống thành `null`.
- Chạy lại luôn hội tụ về cùng một tập point. Nếu một tài liệu ra ít chunk hơn lần trước, các chunk thừa bị xóa (`replace_document`). Đây là bước cần làm sau khi sửa `superseded_by` trong manifest, ví dụ ISSUE-010.
- Tài liệu bị xóa khỏi manifest **không** tự bị xóa khỏi Qdrant. Muốn xóa thì xóa collection rồi ingest lại.

## Cache

Parse cả bộ 30 PDF mất khoảng 1 giờ trên CPU, nên kết quả được cache theo từng tài liệu trong `<data>/cache/` (git bỏ qua vì nằm trong `data/`):
- `parsed/<doc_id>.json`: các trang đã parse. Hết hạn khi PDF đổi (SHA-256), `parse_docling.py` đổi, hoặc phiên bản docling đổi.
- `embedded/<doc_id>.json`: vector dense và sparse. Hết hạn khi nội dung chunk đổi, hoặc `MODEL` hay `MAX_LENGTH` của `embed.py` đổi.

File cache hỏng thì được tính lại. File được ghi kiểu atomic, nên dừng giữa chừng không để lại file dở. Sửa `chunk.py` thì không cần parse lại: chunk mới được embed lại, còn kết quả parse dùng lại từ cache.

## Kiểm thử

- `pytest tests/unit/test_ingest.py`: parser và embed giả, Qdrant chạy trong bộ nhớ.
- `pytest -m integration tests/integration/test_ingest.py`: docling, bge-m3 và Qdrant thật, chạy trên PDF sinh ra lúc test, dùng collection `test_bank_docs_*` riêng rồi xóa đi. `QDRANT_TEST_URL` chọn Qdrant dùng để test.
