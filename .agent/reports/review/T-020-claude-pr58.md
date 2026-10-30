---
id: review-t020-claude-pr58
title: T-020 archived independent Claude review on PR58
type: report
domain: security
module: pii
tags: [review, t-020, pr58, claude, evidence]
priority: 1
---
# T-020 independent Claude review evidence

## Record Metadata

- **Owner**: `teammate-b`
- **Reviewer**: `caitoithap (separate Claude Code session, as stated in source)`
- **Recorder**: `codex-b`; transcription only, not the reviewer
- **Executor**: `codex-b`
- **Status**: `changes-required`
- **Decision**: `CHANGES_REQUESTED`
- **Task ID**: `T-020`
- **Report Date**: `2026-10-30`
- **Reviewed Head**: `1bd48be`

## Review Scope and Provenance

Source: https://github.com/caitoithap/bank-assistant/pull/58#issuecomment-6515181908

This archives the existing external review exactly as retrieved from GitHub.
The recorder did not perform that Claude review, rerun its commands on the
reviewer's behalf, or approve subsequent fixes. The source requests changes;
this is evidence of a separate Claude review under DEC-004, not an approval.
Corrections require independent re-review; task remains in review.

Coordinator follow-up: https://github.com/caitoithap/bank-assistant/pull/58#issuecomment-6515242912
states that item 5 was completed in 4bf3a17. That commit was fast-forwarded
before implementation; coordinator-owned current-context is preserved.

## Original Review

## Review T-020 tại `1bd48be` (phiên Claude Code riêng, theo DEC-004)

**Kết luận: code sạch, test tốt, nhưng còn vài dạng viết số rất phổ biến ở VN đang lọt qua bộ che. Cần sửa trước khi merge.**

### Đã kiểm chứng
- `make check`: 426 passed, 24 deselected, Ruff pass, `FRAMEWORK_VALIDATION_PASS`. `pytest tests/security`: 113 passed. `git diff --check` sạch, CI xanh cả 4 job.
- Acceptance criteria đạt: mỗi entity có ca dương và ca âm. `NoOpNlpEngine` không tải spaCy (có test chặn `spacy.load`). Kết quả không đổi khi che lại lần nữa. Xử lý chồng lấn theo span dài nhất rồi mới theo độ ưu tiên là hợp lý. Log không chứa giá trị gốc.
- Fix F-T020-01 (`+84900000001 100 VND` → `<PHONE_NUMBER> 100 VND`) đúng. Test audit cập nhật hợp lý với bộ che thật.
- Pin `presidio-analyzer==2.2.365` vì CI dùng Python 3.10: OK.

### Cần sửa trước khi merge
Mình chạy `mask_text` trên các chuỗi giả dưới đây. FR-06/NFR-05 yêu cầu "0 PII gốc trong log/trace", nên các dạng phổ biến phải được che:

| Input | Kết quả hiện tại |
|---|---|
| `CCCD: 001 204 012 345` | **không che** |
| `STK 1903 6789 0123` | **không che** |
| `STK: 0011-0049-12345` | **không che** |
| `(+84) 912 345 678` | **không che** |
| `SĐT0912345678` / `sdt0912345678` | **không che** (vì lookbehind `(?<![\w+])` coi chữ cái liền trước là một phần của từ) |
| `gọi 090.123.4567 nhé`, `+84-912-345-678`, `0912 345 678 và 0987654321` | che đúng |

Đề xuất:
1. **CCCD và STK có dấu phân cách:** cho phép nhóm số cách nhau bởi dấu cách, chấm hoặc gạch ngang, giống cách đã làm với điện thoại (ví dụ CCCD = 12 chữ số với `[ .-]?` giữa các chữ số, hoặc nhóm 3-3-3-3 / 4-4-4). STK: tổng 8–19 chữ số, chia nhóm bằng dấu phân cách. Có thể che thừa (ví dụ một dãy số tiền viết tách nhóm), nhưng thống nhất với hướng "ưu tiên riêng tư" mà doc đã ghi.
2. **`(+84)`:** cho phép mã quốc gia có ngoặc `\(\+84\)[ .-]?`.
3. **Nhãn dính liền số (`SĐT0912…`):** với điện thoại, đổi lookbehind thành chỉ chặn chữ số hoặc `+` (`(?<![0-9+])`) thay vì mọi `\w`. Khi đó `ref0900000001` sẽ bị che. Đây là che thừa có chủ ý; cần sửa test âm tương ứng và ghi lại lựa chọn này trong doc.
4. Thêm các chuỗi trên vào `tests/security/test_pii.py` làm regression.

### Sổ sách
5. `current-context.md` chưa có T-020 `review` và E-007 `EPIC_IN_PROGRESS` (`epics.md` đã đổi). Mô tả PR ghi để coordinator A đồng bộ. Bên A sẽ lo phần này, B không cần sửa.
6. Sau khi sửa xong, nhờ B lưu review này thành `.agent/reports/review/T-020-claude-pr58.md` (giống `T-014-claude-pr49.md`) để đáp ứng DEC-004.

### Ghi chú (không chặn merge)
7. Khi PR này merge, audit của T-015 sẽ chuyển từ `[REDACTED]` toàn bộ câu hỏi sang chỉ che 3 loại entity. Với FR-06 thì đúng phạm vi, nhưng những thông tin khác như tên hay email sẽ nằm trong `question_masked`. Nên ghi một dòng trong `docs/07-development/audit.md`.
8. Chữ số full-width (`０９…`) đang được chủ ý bỏ qua. Ít gặp, chấp nhận được.
