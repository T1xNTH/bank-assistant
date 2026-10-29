---
id: issue-013
title: "Không xóa bảng số tiền khi fallback chỉ đọc thêm chữ"
type: governance
domain: rag
module: src/app/rag/parse_docling.py
tags: [issue, t-006, pr-30, pr30-f05]
priority: 2
---
# ISSUE-013: Fallback nhiều chữ hơn làm mất số tiền

## Usage Purpose

Theo dõi PR30-F05 tại head `7c41113`.

## Record Metadata

- **Issue ID**: `ISSUE-013`
- **Title**: Không xóa bảng số tiền khi fallback chỉ đọc thêm chữ
- **Owner**: `trong-hung`
- **Reporter**: `codex`
- **Status**: `resolved`
- **Issue Type**: `defect`
- **Priority**: `2`
- **Created Date**: `2026-10-28`
- **Target Date**: `none`

## Description

`_repair` chỉ so số chữ cái trước khi thay toàn bộ nội dung trang và xóa tables. Một bảng tiền ít chữ bị xem là gần rỗng dù có số liệu quan trọng.

## Impact

- **Affected Scope**: Near-empty OCR fallback, T-006.
- **Severity**: `medium`
- **User or Delivery Impact**: Số tiền có trong kết quả OCR gốc có thể biến mất khi fallback chỉ đọc được đoạn chữ khác của trang.

## Reproduction Evidence

- **Preconditions**: Trang `Ký tên`, bảng STT/So tien với `22.700.000` và `3.000.000`, tổng chữ cái dưới 200.
- **Steps**: Chạy `.review-worktrees/pr30-test-env/Scripts/python.exe .review-worktrees/pr30_r4_probes.py`; renderer và kết quả Tesseract được thay bằng dữ liệu giả lập.
- **Observed Result**: Fallback `Ngân hàng xác nhận chữ ký của người đại diện.` có nhiều chữ cái hơn, được chọn; tables rỗng và cả hai số tiền mất.
- **Expected Result**: Không bỏ số liệu gốc chỉ vì fallback có nhiều chữ cái hơn.
- **Evidence Paths**: `.review-worktrees/pr30_r4_probes.py`, review vòng 4 cục bộ `PR-030-B-round-4`; [kiểm chứng và bản sửa tiếp theo](../../reports/implementation/T-006-PR30-final-fixes.md). Phép tái hiện ban đầu không chạy model; kiểm chứng sau sửa có replay cả 7 fallback từ corpus thật.

## Related Files

- **Affected Files**: `src/app/rag/parse_docling.py:323-326`, test repair.
- **Tasks or Epics**: `T-006`, `E-003`
- **Decisions**: `CR-007`
- **Risks**: `none`
- **Blockers**: `none`

## Acceptance Criteria

- [x] Fallback nhiều chữ nhưng thiếu số liệu không được làm mất bảng gốc.
- [x] Kiểm tra độ phủ nội dung trước khi thay trang, hoặc giữ phần chưa được fallback phục hồi.
- [x] Có regression test cho bảng ít chữ và số tiền bị fallback bỏ sót.

## Resolution

- **Resolution Type**: `fixed`
- **Resolution Summary**: Plain OCR fallback retains structured numerical tables because prose cannot establish row/column coverage. Code: `f0eaeac92d2cce726fb6054447812f6a5384e72a`.
- **Verification Evidence**: [Implementation report](../../reports/implementation/T-006-PR30-final-fixes.md); 101 unit tests and 3 OCR integration tests pass; regression tests fail on the old parser. Corpus replay covers 443 scan selections and 7 fallbacks; all 3 rotation-branch pages were rerun with real OCR (9 conversions).
- **Resolved By**: `codex`
- **Resolved Date**: `2026-10-29`

Resolution records an implemented and tested fix, not independent PR approval.

## Completion Criteria

- [x] Đạt acceptance criteria hoặc có chấp nhận rủi ro được duyệt.
- [x] Liên kết bằng chứng khắc phục.
- [x] Có xác nhận kiểm tra sau sửa.

## Forbidden Actions

Không coi việc bỏ bảng để tránh lặp là đúng khi chưa xác minh fallback chứa đủ số liệu đó.

## Output Requirements

Liên kết issue với T-006 và report vòng 4.

## Follow-up Implementation

User requested the remaining fixes on 2026-10-29. Code commit `f0eaeac92d2cce726fb6054447812f6a5384e72a`; [implementation and verification](../../reports/implementation/T-006-PR30-final-fixes.md). Independent PR review remains required.
