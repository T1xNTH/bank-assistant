---
id: impl-t-006-pr30-final-fixes
title: "T-006: bảo vệ số liệu khi fallback và chọn hướng xoay"
type: report
domain: rag
module: src/app/rag/parse_docling.py
tags: [implementation, t-006, pr-30, pr30-f04, pr30-f05, pr30-f06]
priority: 2
---
# T-006: sửa các finding còn lại của PR #30

## Usage Purpose

Bổ sung cho [bản sửa F03](T-006-PR30-F03-followup.md), theo yêu cầu người dùng “fix đi” và “triển khai nốt T006”. Giữ nguyên các báo cáo cuối trước đó; không dùng review cũ làm approval cho thay đổi mới.

## Record Metadata

- **Report ID**: `T-006-PR30-final-fixes`
- **Title**: Giữ bảng số liệu khi OCR fallback và tránh chọn hướng xoay vẫn còn rác
- **Owner**: `trong-hung`
- **Executor**: `codex`
- **Status**: `complete`
- **Task ID**: `T-006`
- **Epic ID**: `E-003`
- **Report Date**: `2026-10-29`

## Scope

- **Implemented**: PR30-F04/F05/F06: tỷ lệ có khoảng trắng trước `%`; bảo toàn bảng số liệu trong fallback; không chọn bản xoay chỉ có cải thiện điểm trong vùng chữ rác. Kiểm thử hồi quy và kiểm chứng trên kết quả corpus thật.
- **Not Implemented**: Không đổi model/backend/schema, không đòi OCR đúng mọi ô, không merge hay tự approve PR.

## Changes Made

| File hoặc sản phẩm | Tóm tắt thay đổi | Task ID |
|---|---|---|
| `src/app/rag/parse_docling.py` | Nhận khoảng trắng thường, NBSP và narrow NBSP trước `%`; chuẩn hóa khoảng trắng khi so số liệu, giữ đơn vị và dấu thập phân. Giải mã HTML entity trước khi trích số để `&#124;` không bị coi là số 124. | T-006 |
| `src/app/rag/parse_docling.py` | Khi fallback có nhiều chữ hơn, giữ các bảng gốc có số liệu: OCR thuần không chứng minh được quan hệ hàng/cột còn đủ, kể cả khi nhắc lại cùng các con số. | T-006 |
| `src/app/rag/parse_docling.py` | `_best_rotation` chỉ chấp nhận candidate tốt hơn và đạt `MIN_COMMON_WORD_RATIO` hiện có (0,04). Không thêm ngưỡng riêng theo số dòng hoặc theo file. | T-006 |
| `tests/unit/test_parse_docling_rotation.py` | Năm test cho fallback mất số liệu/đổi dịch vụ, bảng tỉnh bị xoay sai, ứng viên vẫn rác và phục hồi hướng đọc được. | T-006 |
| `tests/unit/test_parse_docling_table_coverage.py` | Bảy ca bổ sung: ba loại khoảng trắng, ba dạng tỷ lệ tương đương nhưng khác đơn vị số trần, HTML escaped pipe. | T-006 |
| `tests/fixtures/ocr/145-page-109.json` | Kết quả OCR thật trước/sau lỗi trên trang PDF 109; kèm SHA256 input và commit parser nguồn, không cần model trong CI. | T-006 |

## Related Files

- **Task Records**: `.agent/execution/tasks/T-006.md`, E-003 trong `.agent/planning/epics.md`.
- **Context Packages**: Lịch sử Codex CLI, corpus 30 PDF từ release `corpus-2026-10-28`, báo cáo đo tại `7c41113`.
- **Task Board**: `.agent/execution/task-board.md`.
- **Current Context**: `.agent/execution/current-context.md`.
- **Decisions**: `DEC-001`, `DEC-004` (review độc lập).
- **Change Requests**: `CR-006`, `CR-007`; sửa lỗi trong phạm vi parser đã duyệt.
- **Risks or Blockers**: `ISSUE-012`, `ISSUE-013`, `ISSUE-016`; giới hạn bên dưới.
- **Review Request**: Reviewer độc lập tiếp theo của PR #30; Codex là implementer.
- **Commits**: `f0eaeac92d2cce726fb6054447812f6a5384e72a` (code/test), sau `7c4111316151d3ff4a35ec7e0f7e34e81f2327a6`; báo cáo và task-commit-map trong commit tài liệu đi kèm.

## Command Evidence

| Lệnh | Kết quả | Bằng chứng |
|---|---|---|
| `agent task start T-006` | not-run | Sửa tiếp PR theo yêu cầu trực tiếp; ghi nhận lại trạng thái task/board và giữ lịch sử cũ. |
| `agent task verify T-006` | not-run | Các kiểm tra trực tiếp ở bảng dưới. |
| `agent task report T-006` | not-run | Tạo report bổ sung, không ghi đè implementation report cuối. |
| `agent review request T-006` | not-run | Bàn giao qua PR, không tự approve hoặc sửa review report cũ. |

## Verification Evidence

| Kiểm tra | Kết quả | Bằng chứng |
|---|---|---|
| Hai module regression mới với parser `7c41113` | passed | 11 failed, 11 passed như kỳ vọng; cả ba lỗi được phát hiện trên code cũ. |
| Hai module regression với bản sửa | passed | 22 passed trên Windows; không cần model OCR. |
| Linux `python -m pytest -q` | passed | 101 passed, 3 deselected, 68,40 giây. |
| Linux `python -m pytest -q -m integration tests/integration/test_parse_docling_pdf.py` | passed | 3 passed, 7 deprecation warnings, 40,83 giây; OCR Tesseract thật. |
| `ruff check .`, framework validator, `git diff --check` | passed | All checks passed, FRAMEWORK_VALIDATION_PASS và không lỗi whitespace trong checkout PR riêng. |
| Phát lại chọn trang và fallback từ corpus | passed | 443 trang scan: không đổi lựa chọn; 7 fallback dùng đúng text Tesseract đã lưu: không đổi kết quả. Không gọi đây là chạy lại model trên 30 PDF. |
| OCR thật các trang đi nhánh xoay | passed | 3 trang, đủ 9 lần chuyển đổi hướng. `145.signed.pdf` tr.109 giữ 30 dòng dữ liệu Markdown thay vì bảng xoay sai 2 dòng; tr.110 không đổi. `17-nhnn.pdf` tr.28 phục hồi đúng như trước, score 0,30625. [Metrics và phương pháp](evidence/T-006-final-fixes.md). |
| Bộ Markdown sau sửa | passed | 30 file/666 trang, chỉ tr.109 khác bản chạy trước. 663 trang không đi nhánh xoay được tái sử dụng từ lần chạy đầy đủ; không tuyên bố đã OCR lại mọi trang. ZIP cục bộ `output/pr30-fixed-markdown-20261028.zip`. |

## Deviations

- **Plan Deviations**: Bản task metadata cũ còn `pending` trong khi board ghi `done`, dù PR đang mở và có finding mới. Bản bàn giao mới đồng bộ về `review`, ghi correction trong lịch sử phiên; không sửa các approval cũ hoặc đánh dấu `done`.
- **Approved By**: Người dùng yêu cầu triển khai tiếp trong phiên ngày 2026-10-29; không phải approval review độc lập.
- **Known Limitations**: F04/F05 được tái hiện bằng regression; lần đo corpus trước chưa thấy hai đường lỗi này. Fallback có thể lặp text của bảng vì ưu tiên giữ quan hệ hàng/cột. Candidate xoay có điểm dưới 0,04 bị giữ nguyên ngay cả khi tốt hơn một phần; đây là lựa chọn bảo thủ, không phục hồi mọi thiếu sót của OCR gốc. Các bảng tên/mã tỉnh vẫn còn ô nhận sai hoặc bỏ trống. F03 vẫn có thể bổ sung bảng gốc nhiễu; không tự sửa thêm ngoài phạm vi ba finding này.

## Completion Criteria

- [x] Mọi thay đổi ánh xạ tới T-006 và finding cụ thể.
- [x] Test hồi quy phân biệt code trước/sau sửa.
- [x] Ghi rõ kết quả test/lint/integration và giới hạn.
- [x] Hoàn tất kiểm chứng OCR thật các trang xoay.
- [x] Cập nhật commit map và bàn giao review độc lập qua PR; T-006 vẫn ở review.

## Forbidden Actions

Không dùng báo cáo này thay review độc lập, không sửa approval lịch sử, không tuyên bố OCR chính xác tuyệt đối hoặc đã chạy lại model trên cả corpus trong lượt sửa này.

## Output Requirements

Code, test, issue resolution và báo cáo được cập nhật trên PR #30. T-006 ở `review` cho tới khi có review/merge theo quy trình.
