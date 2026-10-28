---
id: development-corpus
title: Corpus
type: reference
domain: development
module: data
tags: [development, data, corpus, manifest, t-005]
priority: 3
---
# Bộ tài liệu M-001 (`data/`)

## Nguyên tắc

- `data/manifest.csv` được commit. PDF **không** được commit (`.gitignore` bỏ qua `data/*`), mỗi người tự dựng lại trên máy mình.
- Tên file trong `data/` phải **đúng y** cột `file` của manifest, kể cả chữ hoa/thường.
- Kiểm tra sau khi dựng: `python scripts/check_manifest.py` phải ra `OK data/manifest.csv: 0 lỗi`. Script kiểm cả việc file thật sự là PDF (bắt đầu bằng `%PDF-`), nên một trang HTML đổi đuôi `.pdf` sẽ bị báo lỗi.

## Dựng lại 30 file

**23 file có link PDF trực tiếp** (`datafiles.chinhphu.vn`, `vietinbank.vn/assets/...`): tải về và lưu đúng tên cột `file`.

```bash
# Linux/macOS/Git Bash; trên Windows PowerShell dùng Invoke-WebRequest -OutFile
python - <<'PY'
import csv, urllib.request
for r in csv.DictReader(open("data/manifest.csv", encoding="utf-8")):
    if "/bieu-phi-dich-vu/" not in r["source_url"]:
        req = urllib.request.Request(r["source_url"], headers={"User-Agent": "Mozilla/5.0"})
        open(f"data/{r['file']}", "wb").write(urllib.request.urlopen(req).read())
PY
```

**7 biểu phí VietinBank** (`doc_id` bắt đầu bằng `vtb-bieu-phi-`): `source_url` là trang web, VietinBank không có file PDF gốc. Phải in trang ra PDF:

1. Mở `source_url` bằng Chrome hoặc Firefox, chờ bảng phí tải xong.
2. `Ctrl+P` → máy in **Save as PDF / Lưu dưới dạng PDF**, khổ **A4**, hướng **dọc**, lề mặc định.
3. Lưu vào `data/` với tên **đúng cột `file`**, ví dụ `dichvunhdt.pdf`.
4. Chạy `python scripts/check_manifest.py`.

| `file` | `source_url` (trang cần in) |
|---|---|
| `bieuphiapdungsptheqt.pdf` | `.../bieu-phi-ap-dung-cho-san-pham-the-tin-dung-quoc-te-41-html` |
| `bieuphidichvutttqtvtb.pdf` | `.../bieu-phi-ap-dung-cho-nghiep-vu-thanh-toan-the-tin-dung-quoc-te-41-html` |
| `dichvsptheghinoqt.pdf` | `.../bieu-phi-dich-vu-ap-dung-cho-san-pham-the-ghi-no-quoc-te-41-html` |
| `dichvunhdt.pdf` | `.../dich-vu-ngan-hang-dien-tu-41-html` |
| `dichvutaikhoanthanhtoan.pdf` | `.../dich-vu-tai-khoan-thanh-toan-tien-gui-41-html` |
| `dichvuthanhtoanchuyentienvtb.pdf` | `.../dich-vu-thanh-toan-chuyen-tien-41-html` |
| `sptheghinonoidia.pdf` | `.../bieu-phi-ap-dung-cho-san-pham-the-ghi-no-noi-dia-danh-cho-khach-hang-doanh-nghiep-va-ho-kinh-doanh-41-html` |

`...` là `https://www.vietinbank.vn/doanh-nghiep/cong-cu-tien-ich/bieu-phi-dich-vu`; link đầy đủ có trong manifest. Bản in của mỗi người có thể khác nhau về ngắt trang hoặc ngày in (mã hash khác nhau), nhưng nội dung bảng phí như nhau. Nếu VietinBank cập nhật biểu phí thì cập nhật `effective_date` trong manifest. Bản dùng cho T-005 được in ngày 2026-10-27. Cả 7 file là biểu phí cho **khách hàng doanh nghiệp**.

## Quy ước `superseded_by`

- Retrieval loại mọi chunk có `superseded_by` khác rỗng (`docs/02-architecture/architecture.md`), chưa lọc theo ngày hiệu lực. Vì vậy chỉ đặt `superseded_by` khi văn bản thay thế **đã có hiệu lực**. `check_manifest.py` báo lỗi nếu văn bản thay thế chưa có hiệu lực hoặc không mới hơn văn bản bị thay.
- Các cặp hiện có: `tt39-2016-vbhn06` → `tt39-2016-vbhn86` (cho vay, từ 2026-08-15) và `nd74-2024` → `nd293-2025` (lương tối thiểu, từ 2026-01-01).
- **Việc theo lịch (ISSUE-010):** từ **2026-11-09**, đặt `tt26-2021` có `superseded_by = tt26-2021-vbhn` (VBHN 112 gồm cả TT 48/2026). Trước ngày đó cả hai đều được truy xuất.
- Thông tư sửa đổi (TT 25, 29, 48/2026) vẫn được truy xuất song song với văn bản hợp nhất tương ứng.
