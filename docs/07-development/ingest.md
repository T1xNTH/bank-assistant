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

Trên Windows, tiến độ được in ra theo UTF-8, kể cả khi chuyển hướng output ra file. Cần Tesseract (`tooling.md`) và mạng ở lần chạy đầu để tải model của docling và bge-m3. Kết nối Qdrant lấy từ `QDRANT_URL` (mặc định `http://127.0.0.1:6333`) và `QDRANT_API_KEY`.

## Hành vi

- Manifest được kiểm bằng `scripts/check_manifest.py` trước. Có lỗi thì dừng, chưa ghi gì.
- Mỗi tài liệu in một dòng tiến độ (số trang, số chunk, bước nào lấy từ cache, thời gian). Cuối cùng in tóm tắt: số tài liệu thành công, số trang, số chunk, tổng số point trong collection và tổng thời gian.
- Một tài liệu lỗi (ví dụ `ParseError`) được báo và bỏ qua, các tài liệu khác vẫn được ingest. Có tài liệu lỗi thì exit code là 1.
- Payload gồm đủ 9 trường của `docs/05-database/schema.md`: `source`, `page`, `chunk_index`, `text` lấy từ chunk; `doc_id`, `department`, `classification`, `effective_date`, `superseded_by` lấy từ manifest. Ô `superseded_by` để trống thành `null`.
- Chạy lại luôn hội tụ về cùng một tập point. Nếu một tài liệu ra ít chunk hơn lần trước, các chunk thừa bị xóa (`replace_document`). Đây là bước cần làm sau khi sửa `superseded_by` trong manifest, ví dụ ISSUE-010.
- Tài liệu bị xóa khỏi manifest **không** tự bị xóa khỏi Qdrant. Muốn xóa thì xóa collection rồi ingest lại.

## Cách chia chunk

`chunk_pages` (`src/app/rag/chunk.py`, CR-009) chia theo cấu trúc văn bản, không theo trang:
- Văn bản pháp luật được cắt ở Phần, Chương, Mục, Điều và Phụ lục, kể cả trang OCR không có `## ` và số La Mã bị OCR đọc sai (IH, VH, VỊ, H, EV). Dòng bắt đầu như tiêu đề nhưng tiếp theo là chữ thường ("Phụ lục II ban hành kèm theo…") vẫn là nội dung. Văn bản không có các đầu mục này (biểu phí, điều khoản ngân hàng) được cắt ở tiêu đề `## ` của docling; biểu phí không có tiêu đề lấy dòng đầu làm tiêu đề.
- Mỗi chunk mở đầu bằng một dòng đường dẫn tiêu đề, ví dụ `Chương III … › Mục 1 … › Điều 13. Mức lương hưu hằng tháng`, tối đa `size // 4` ký tự. Phần mở đầu văn bản (quốc hiệu, căn cứ) không có dòng này.
- Không mất chữ của tiêu đề nào: tiêu đề không vừa đường dẫn thì nằm ở đầu nội dung; Điều không có nội dung (ví dụ "Điều 6. (được bãi bỏ)") thành một chunk riêng.
- Một Điều vắt qua hai trang là một khối liền; `page` là trang bắt đầu của chunk. Bảng vẫn chia giữa các hàng, lặp lại header, thêm dòng tiêu đề của đầu mục chứa bảng.

Đổi cách chia thì chạy lại `scripts/ingest.py`: chỉ phải embed lại, kết quả parse lấy từ cache.

## Cache

Parse cả bộ 30 PDF mất khoảng 1 giờ trên CPU, nên kết quả được cache theo từng tài liệu trong `<data>/cache/` (git bỏ qua vì nằm trong `data/`):
- `parsed/<doc_id>.json`: các trang đã parse. Hết hạn khi PDF đổi (SHA-256), `parse_docling.py` đổi, hoặc phiên bản docling đổi.
- `embedded/<doc_id>.json`: vector dense và sparse. Hết hạn khi nội dung chunk đổi, hoặc `MODEL` hay `MAX_LENGTH` của `embed.py` đổi.

Khóa cache **không** gồm: phiên bản docling-core, docling-parse, docling-ibm-models, Tesseract và dữ liệu ngôn ngữ của nó; mã của `embed.py` ngoài `MODEL`/`MAX_LENGTH` (ví dụ `to_sparse`) và phiên bản FlagEmbedding. Đổi một trong các thứ đó thì chạy lại với `--no-cache`. Tên file trích dẫn (`source`) luôn lấy theo manifest hiện tại, nên đổi tên file mà giữ nguyên nội dung vẫn dùng được cache.

File cache hỏng hoặc sai cấu trúc thì được tính lại. File được ghi kiểu atomic, nên dừng giữa chừng không để lại file dở. Sửa `chunk.py` thì không cần parse lại: chunk mới được embed lại, còn kết quả parse dùng lại từ cache.

## Kiểm thử

- `pytest tests/unit/test_ingest.py`: parser và embed giả, Qdrant chạy trong bộ nhớ.
- `pytest -m integration tests/integration/test_ingest.py`: docling, bge-m3 và Qdrant thật, chạy trên PDF sinh ra lúc test, dùng collection `test_bank_docs_*` riêng rồi xóa đi. `QDRANT_TEST_URL` chọn Qdrant dùng để test.
