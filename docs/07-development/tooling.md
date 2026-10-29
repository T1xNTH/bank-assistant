---
id: development-tooling
title: Tooling
type: reference
domain: development
module: tooling
tags: [development, tooling, setup, ocr]
priority: 3
---
# Công cụ và cài đặt

## Python

```bash
make setup     # tạo .venv, cài requirements-dev.txt (kéo theo requirements.txt)
make check     # ruff + pytest + validate framework
```

`requirements.txt` cài torch **bản CPU** qua `--extra-index-url https://download.pytorch.org/whl/cpu`, vì máy dev không có GPU dùng được. Lần đầu cài tải khoảng 1–2 GB.

## Tesseract (OCR cho ingest, E-003)

`src/app/rag/parse_docling.py` dùng Tesseract để OCR PDF scan, với dữ liệu tiếng Việt `vie`. Tesseract là chương trình cài vào hệ thống, không cài qua `pip`, và chỉ chạy CPU.

**Ubuntu/Debian**
```bash
sudo apt install -y tesseract-ocr tesseract-ocr-vie
tesseract --list-langs    # phải có dòng: vie
```

**Windows**
1. Tải bản cài từ https://github.com/UB-Mannheim/tesseract/wiki và chạy.
2. Ở bước *Additional language data*, tick **Vietnamese**.
3. Thêm `C:\Program Files\Tesseract-OCR` vào biến môi trường `PATH`, rồi mở terminal mới.
4. Kiểm tra: `tesseract --list-langs` có dòng `vie`.

Chưa cài Tesseract thì unit test vẫn chạy được, còn `pytest -m integration` sẽ skip các test parser.

## Xem thử kết quả parse trên tài liệu thật

```bash
PYTHONPATH=src .venv/bin/python scripts/parse_preview.py              # mọi data/*.pdf
PYTHONPATH=src .venv/bin/python scripts/parse_preview.py data/x.pdf   # một file
```

Mỗi PDF được ghi thành `data/parsed/<tên>.md` (thư mục này bị git ignore). Mỗi file in ra một dòng tóm tắt gồm số trang, số bảng và số trang rỗng. Lần chạy đầu tải model layout và bảng của docling (vài trăm MB).
