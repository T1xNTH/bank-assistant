---
id: review-t014-claude-pr49
title: T-014 archived independent Claude review on PR49
type: report
domain: security
module: src/app/security/auth.py
tags: [review, t-014, pr49, claude, evidence]
priority: 2
---
# T-014 independent Claude review evidence

## Record Metadata

- **Owner**: `teammate-b`
- **Reviewer**: `caitoithap (separate Claude Code session, as stated in source)`
- **Recorder**: `codex`; transcription only, not the reviewer
- **Executor**: `codex`
- **Status**: `approved`
- **Decision**: `APPROVED` (technical assessment in the source comment)
- **Task ID**: `T-014`
- **Report Date**: `2026-10-29`
- **Reviewed Head**: `566672b`

## Review Scope and Provenance

Source: https://github.com/caitoithap/bank-assistant/pull/49#issuecomment-6491355700

This file archives the existing external review, including its reported commands
and results. The recorder did not perform that review or rerun those commands
on the reviewer's behalf. The original comment identifies a separate Claude
session and approves the code technically, while requiring prerequisite merge,
review evidence recording and Compose conflict resolution before merge.
This is not a new GitHub approval or a review of the subsequent merge resolution.
Previous review reports remain immutable. T-014 remains in review.

## Original Review

## Review T-014 (phiên Claude Code riêng, chỉ đọc diff, report và chạy test)

**Kết luận: code OK, approve về mặt kỹ thuật. Chưa merge ngay vì còn 2 việc quy trình (bên dưới).**

### Đã kiểm chứng
- Chạy lại trên head `566672b`: `pytest tests/security` 25 passed; `make check` 183 passed, 11 deselected, Ruff pass, `FRAMEWORK_VALIDATION_PASS`. Khớp số trong PR, CI xanh cả 4 job.
- Acceptance criteria đạt: thiếu/rỗng/sai `X-API-Key` → 401, `require_role('approver')` sai role → 403, `AUTH_BACKEND` gõ sai → 503 (không mở quyền).
- Registry chỉ lưu SHA-256; registry hỏng/thiếu/role lạ → fail closed 503, không lộ key hay đường dẫn.
- `make_key.py` kiểm tra registry trước khi ghi, ghi bằng tempfile cùng thư mục + `os.replace` → không có file JSON ghi dở.
- Compose mount cả thư mục `config/` read-only (không mount một file), nên thay file bằng `os.replace` vẫn thấy ngay trong container. Dockerfile không copy `config/` nên mount không đè gì; `config/api_keys.json` đã nằm trong `.gitignore`.

### Nhận xét nhỏ (không chặn merge)
1. Mỗi request đọc + parse lại file JSON. Chủ ý để thu hồi key không cần restart; ổn khi registry nhỏ.
2. Một record hỏng làm mọi request 503. An toàn, nhưng nên ghi chú cho vận hành biết.
3. Chạy hai `make_key.py` cùng lúc có thể mất một key (đọc, sửa, ghi không lock). Hiện tạo key bằng tay nên chưa cần sửa.
4. `Settings`: `auth_backend`/`api_keys_file` đọc env lúc gọi, còn `rag_backend`/`llm_backend` vẫn đọc lúc import. Hơi lệch nhau nhưng đúng.

### Cần xử lý trước khi merge
1. **Thứ tự merge:** base đang là `docs/T-004-closure`. Merge #48 trước (đang chờ review), rồi retarget PR này sang `main`.
2. **DEC-004:** cần review report từ phiên Claude riêng; report hiện tại (`T-014-round-2.md`) là từ Codex. Có thể dùng chính review này làm evidence (mình có thể ghi thành `.agent/reports/review/` nếu cần), hoặc thêm governance record cho phép ngoại lệ.
3. **Conflict với #50 (T-011)** ở service `api` trong `infrastructure/compose.yaml`: #50 bỏ `env_file` và thêm `environment:`, PR này thêm `volumes:` ngay cạnh. Ai merge sau thì giữ cả hai phần; #50 đã có sẵn `API_KEYS_FILE`, khớp với PR này.
