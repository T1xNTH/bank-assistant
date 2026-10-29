---
id: issue-012
title: "Nhận diện tỷ lệ có khoảng trắng trước dấu phần trăm"
type: governance
domain: rag
module: src/app/rag/parse_docling.py
tags: [issue, t-006, pr-30, pr30-f04]
priority: 2
---
# ISSUE-012: Tỷ lệ có khoảng trắng không được bảo vệ

## Usage Purpose

Theo dõi PR30-F04 tại head `7c41113`.

## Record Metadata

- **Issue ID**: `ISSUE-012`
- **Title**: Nhận diện tỷ lệ có khoảng trắng trước dấu phần trăm
- **Owner**: `trong-hung`
- **Reporter**: `codex`
- **Status**: `resolved`
- **Issue Type**: `defect`
- **Priority**: `2`
- **Created Date**: `2026-10-28`
- **Target Date**: `none`

## Description

`_FIGURE` không nhận số nguyên có khoảng trắng trước `%`, nên bảng chỉ chứa `4 %` và `5 %` bị `_with_lost_tables` bỏ qua.

## Impact

- **Affected Scope**: OCR page/table selection, T-006.
- **Severity**: `medium`
- **User or Delivery Impact**: Có thể mất cả bảng phí khi bản ảnh bỏ bảng nhưng đoạn văn còn lại có score cao hơn.

## Reproduction Evidence

- **Preconditions**: Đoạn văn đọc được trên 200 chữ cái; bảng OCR không dấu trên 50 chữ cái; kết quả bản ảnh không có bảng.
- **Steps**: Chạy `.review-worktrees/pr30-test-env/Scripts/python.exe .review-worktrees/pr30_r4_probes.py`.
- **Observed Result**: `_figures(table)` rỗng, `choose_pages` chọn bản không có bảng và `_repair` không phục hồi.
- **Expected Result**: Khoảng trắng trước `%` không khiến bảng phí bị coi là không có số liệu.
- **Evidence Paths**: `.review-worktrees/pr30_r4_probes.py`, review vòng 4 cục bộ `PR-030-B-round-4`; [kiểm chứng và bản sửa tiếp theo](../../reports/implementation/T-006-PR30-final-fixes.md). Phép tái hiện ban đầu dùng OCR giả lập; lần đo corpus chưa thấy đường lỗi này.

## Related Files

- **Affected Files**: `src/app/rag/parse_docling.py:68,271`, test table coverage.
- **Tasks or Epics**: `T-006`, `E-003`
- **Decisions**: `CR-007`
- **Risks**: `none`
- **Blockers**: `none`

## Acceptance Criteria

- [x] Nhận diện và chuẩn hóa khoảng trắng thường/NBSP trước `%`.
- [x] Bảng tỷ lệ `4 %`/`5 %` bị mất ở bản ảnh được giữ/phục hồi.
- [x] Regression test đạt và không đánh đồng tỷ lệ với số không có đơn vị `%`.

## Resolution

- **Resolution Type**: `fixed`
- **Resolution Summary**: Spaced percentages are recognized and normalized with the percent unit intact; HTML escaped pipes are excluded from figures. Code: `f0eaeac92d2cce726fb6054447812f6a5384e72a`.
- **Verification Evidence**: [Implementation report](../../reports/implementation/T-006-PR30-final-fixes.md); 101 unit tests and 3 OCR integration tests pass; regression tests fail on the old parser. Corpus replay covers 443 scan selections and 7 fallbacks; all 3 rotation-branch pages were rerun with real OCR (9 conversions).
- **Resolved By**: `codex`
- **Resolved Date**: `2026-10-29`

Resolution records an implemented and tested fix, not independent PR approval.

## Completion Criteria

- [x] Đạt acceptance criteria hoặc có chấp nhận rủi ro được duyệt.
- [x] Liên kết bằng chứng khắc phục.
- [x] Có xác nhận kiểm tra sau sửa.

## Forbidden Actions

Không coi phép tái hiện tổng hợp là bằng chứng một PDF thật đã bị mất bảng.

## Output Requirements

Liên kết issue với T-006 và report vòng 4.

## Follow-up Implementation

User requested the remaining fixes on 2026-10-29. Code commit `f0eaeac92d2cce726fb6054447812f6a5384e72a`; [implementation and verification](../../reports/implementation/T-006-PR30-final-fixes.md). Independent PR review remains required.
