---
id: impl-t-042-pr97-fixes
title: T-042 PR 97 review follow-up
type: report
domain: ui
module: ui
tags: [implementation, T-042, pr-97]
priority: 2
---
# T-042 PR 97 review follow-up

## Record Metadata

- **Owner**: `trong-hung`
- **Executor**: `claude`
- **Status**: `complete`
- **Date**: `2026-11-03`
- **Scope**: B (Codex) review CHANGES_REQUESTED tại `aac79f1`: F-01 [P2], F-02 [P3]
- **Commit**: `e1c1cf8`, `d760b77`; merge main `381566e`

## Changes

- **F-01** `ui/app.py`: `decide()` lưu kết quả quyết định (thread id, duyệt/từ chối, `status`, `answer` của agent) vào session rồi `st.rerun()`. Panel duyệt hiện banner "đã duyệt/đã từ chối · trạng thái: hoàn tất/đang chờ duyệt tiếp" và "Kết quả từ agent: …" (có mã ticket khi tạo ticket). Kết quả giữ tới quyết định sau, không mất khi trang chạy lại. Áp dụng cho cả thread trong phiên và thread nhập bằng id. Lỗi API (404 thread lạ, 409 đã quyết) hiện kèm thread id.
- **F-01 test** `tests/unit/test_ui.py` (AppTest với FastAPI thật, xác thực API key, SQLite): thread tạo ở phiên trình duyệt khác rồi duyệt bằng id, kết quả chứa mã ticket đọc từ `tickets.db` và vẫn hiện sau một lần chạy lại; từ chối kèm ghi chú rồi quyết định trùng ra HTTP 409; thread id lạ ra HTTP 404. Hai test đầu fail trên `ui/app.py` của `aac79f1`, pass sau khi sửa.
- **F-02**: `.agent/execution/tasks/T-042.md` Status `review`, `.agent/execution/tasks/T-031.md` Status `done`, khớp task board.

## Verification

- `pytest tests/unit/test_ui.py`: 13 passed (10 cũ + 3 mới).
- `make check` sau merge main `381566e`: 1104 passed, 79 deselected; Ruff; `FRAMEWORK_VALIDATION_PASS`.
- Chưa giải quyết: AC "Kịch bản demo chạy trọn trên UI — verify: docs/00-project/demo-script.md" tham chiếu file thuộc T-043 chưa có; chờ A (owner) chốt cách kiểm chứng.
