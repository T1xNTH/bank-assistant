---
id: issue-017
title: "PR35-F01: bảng một hàng vượt size bị bỏ toàn bộ"
type: governance
domain: rag
module: src/app/rag/chunk.py
tags: [issue, t-007, pr-35, pr35-f01, data-loss]
priority: 2
---
# ISSUE-017: Mất bảng một hàng khi chia chunk

## Record Metadata

- **Issue ID**: `ISSUE-017`
- **Owner**: `trong-hung`
- **Reporter**: `codex`
- **Status**: `resolved`
- **Issue Type**: `defect`
- **Priority**: `2`
- **Created Date**: `2026-10-29`
- **Related Work**: `T-007`, `E-003`, PR #35, head `6119539`.

## Description

`_table_chunks` trả bảng ngắn trực tiếp; khi bảng dài hơn size, hàm lấy hai dòng đầu làm header và lặp qua rows. Với Markdown chỉ có header + separator, `rows=[]`, không có chunk nào được tạo. Đây là định dạng Docling thật sự xuất cho TableData một hàng, kể cả khi ô không được đánh dấu column_header. Nội dung hàng đó có thể là dữ liệu, không chỉ tên cột.

## Reproduction Evidence

- Code: `.review-worktrees/pr-35/src/app/rag/chunk.py:123-134`, tại `6119539afa4759eb9b46079eb7c130fbea404530`.
- Probe: `.review-worktrees/pr35_round2_probes.py`; kết quả `output/pr35-review-20261029/round2-probes.json`.
- DoclingDocument/TableData 1 hàng 2 cột chứa điều kiện dịch vụ dài và `22.700.000`: exporter tạo Markdown 2 dòng, 2.083 ký tự trước compact, 1.046 sau compact; chunk_pages mặc định 800/100 trả `[]`.
- Corpus thật: `52-nd-cp.signed.pdf` trang 56, input text rỗng và có đúng một bảng. `chunk_pages([page], size=500, overlap=50)` trả `[]`, mất toàn bộ trang dù parser đã trả nội dung bảng. Đây không phải chạy lại hoặc khẳng định độ đúng OCR.
- Có 11 bảng hai dòng trong snapshot corpus: size 800 không mất bảng thật nào; size 500 mất 1 bảng; size 300 mất 3; size 100 mất 8.

## Impact

- **Severity**: `medium` (P2 / major trong review).
- **Affected Scope**: Nội dung bảng và trang được ingest ở T-010.
- **User or Delivery Impact**: Dữ liệu biến mất trước embedding; cấu hình size hợp lệ có thể làm mất nguyên trang mà không báo lỗi.

## Acceptance Criteria

- [x] Khi rows rỗng nhưng bảng không rỗng, giữ nguyên bảng như ngoại lệ dòng dài thay vì trả danh sách rỗng.
- [x] Test hồi quy cho bảng chỉ có một hàng nội dung + separator vượt size, gồm số tiền và nhiều size hợp lệ.
- [x] Xác minh trang 56 của `52-nd-cp.signed.pdf` không còn mất ở 500/50; giữ nguyên hành vi chia bảng nhiều dòng và header lặp.

## Resolution

- **Resolution Type**: `fixed`
- **Resolution Summary**: Commit `e749541e783dd5dc30b5704bc6c0a30ed665c054` retains a non-empty table when only header/separator remain, applying the existing oversized-row exception. No change to text or multi-row table chunking.
- **Verification Evidence**: [Implementation follow-up](../../reports/implementation/T-007-PR35-F01.md); 25 chunk tests and Linux full suite 129 passed / 6 deselected. Six new regression cases fail on the previous source. Corpus replay on 30 PDFs/666 pages restores 1/3/8 tables at size 500/300/100; default 800 output is unchanged. PDF page 56 now yields one complete chunk at 500/50.
- **Resolved By**: `codex`
- **Resolved Date**: `2026-10-29`

The initial local review PR-035-B-round-2 is retained as historical evidence. The user then requested a direct fix. Codex is now an implementer of this patch; this resolution does not constitute independent approval of the new code. T-007 remains in review.
