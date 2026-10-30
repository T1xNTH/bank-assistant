---
id: review-t020-claude-pr58-round2
title: T-020 archived separate Claude re-review on PR58 at 28326eb
type: report
domain: security
module: pii
tags: [review, t-020, pr58, claude, round2]
priority: 1
---
# T-020 external Claude re-review evidence

## Record Metadata

- **Owner**: `teammate-b`
- **Reviewer**: `caitoithap (separate Claude Code session, as stated in source)`
- **Recorder**: `codex-b`; transcription only
- **Executor**: `codex-b`
- **Status**: `changes-required`
- **Decision**: `CHANGES_REQUESTED`
- **Task ID**: `T-020`
- **Report Date**: `2026-10-30`
- **Reviewed Head**: `28326eb`

## Review Scope and Provenance

Source: https://github.com/caitoithap/bank-assistant/pull/58#issuecomment-6516910648

This archives the external separate-Claude re-review, not a new review by the
recorder. The source confirms earlier fixes and requests four remaining changes;
no approval of subsequent code is claimed. Task remains in review pending new-head
review and peer approval. Source content is preserved; final blank lines are normalized.

Item 4 explicitly requests removing a blank EOF line from the earlier archive
T-020-claude-pr58.md. Only trailing whitespace is corrected there, preserving its
source body, reviewer identity, decision and reviewed head; this archive records
that requested formatting correction without rewriting the prior review outcome.

## Original Re-review

## Re-review T-020 tại `28326eb` (phiên Claude Code riêng, theo DEC-004)

**Kết luận: các mục cần sửa của review trước đã xử lý đúng. Còn vài điểm nhỏ, nhờ B sửa nốt rồi mình approve.**

### Đã kiểm chứng
- `make check`: 452 passed, 24 deselected, Ruff pass, `FRAMEWORK_VALIDATION_PASS`. `pytest tests/security`: 139 passed. CI xanh cả 4 job.
- Chạy `mask_text` trên 46 chuỗi mẫu. Các chuỗi lọt ở review trước (`CCCD: 001 204 012 345`, `STK 1903 6789 0123`, `STK: 0011-0049-12345`, `(+84) 912 345 678`, `SĐT0912345678`) đều đã che. F-T020-01 vẫn đúng (`+84900000001 100 VND` → `<PHONE_NUMBER> 100 VND`). CCCD tách nhóm có nhãn hay không nhãn (`079 204 012 345`, `CMND …`, `căn cước …`) đều che.
- Sổ sách OK: review cũ lưu đúng `CHANGES_REQUESTED`/head `1bd48be`, commit context `4bf3a17` giữ nguyên, `audit.md` đã ghi chú tên/email có thể còn trong `question_masked`.

### Nhờ B sửa
| # | Input | Kết quả hiện tại | Đề xuất |
|---|---|---|---|
| 1 | `STK1903678901234` | **không che** | Lookbehind của `ACCOUNT_NUMBER` đang là `(?<![\w+])`, nên nhãn STK dính liền số bị bỏ qua. Áp dụng cách đã làm với điện thoại: cho phép nhãn `stk`/`tk` dính liền (hoặc đổi lookbehind thành `(?<![0-9+])` cho STK có nhãn). Thêm regression. |
| 2 | `0912345678abc` | **không che** | Lookahead `(?!\w)` chặn khi chữ cái dính ngay sau số. Có thể đổi thành `(?![0-9])` cho điện thoại (che thừa có chủ ý, giống `ref0900000001`). Thêm regression. |
| 3 | `tài khoản số 1903 6789 0123`, `STK của tôi là 1903 6789 0123` | che nhưng ra `<CCCD>` | Vẫn che nên không lộ PII, nhưng nhãn sai loại. Nới regex nhãn để cho phép vài từ đệm như `số`, `của tôi là` giữa nhãn và số, hoặc ghi rõ giới hạn này trong `security-design.md`. |
| 4 | `.agent/reports/review/T-020-claude-pr58.md` | thừa dòng trống ở cuối file | `git diff --check` báo `new blank line at EOF`. Xóa dòng trống cuối. |

Không có mục nào chặn về bảo mật lớn (3 chỉ là nhãn sai, 4 là định dạng), nhưng 1 và 2 vẫn để lọt số nên nhờ B xử lý luôn trong PR này.
