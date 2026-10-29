---
id: impl-t-006-pr30-f03-followup
title: "T-006: bảo toàn dòng bảng khi chọn kết quả OCR"
type: report
domain: rag
module: src/app/rag/parse_docling.py
tags: [implementation, t-006, pr-30, pr30-f03]
priority: 2
---
# T-006: sửa PR30-F03 sau review vòng 3

## Usage Purpose

Báo cáo bổ sung cho [implementation report T-006](T-006.md), thay thế mô tả ngưỡng giữ 50% tập số trong bản sửa `73b8779`. Giữ nguyên báo cáo cuối và các bằng chứng lịch sử. Người dùng yêu cầu Codex sửa trực tiếp finding sau review; từ thời điểm đó Codex là implementer của bản sửa này, không phải reviewer độc lập cho chính bản sửa.

## Record Metadata

- **Report ID**: `T-006-PR30-F03-followup`
- **Title**: Bảo toàn dòng bảng và quan hệ nhãn–giá trị khi chọn OCR
- **Owner**: `trong-hung`
- **Executor**: `codex`
- **Status**: `complete`
- **Task ID**: `T-006`
- **Epic ID**: `E-003`
- **Report Date**: `2026-10-28`

## Scope

- **Implemented**: Sửa PR30-F03 trong PR #30 từ base `43e736f`; đối chiếu nhãn và số liệu theo dòng trong cùng một bảng; giữ bảng gốc khi chưa chứng minh được các dòng còn đủ; kiểm thử hồi quy.
- **Not Implemented**: Không thay OCR/model/backend, không thêm lượt OCR, không đổi schema, không tự approve/merge PR hoặc đổi task terminal. Không chạy lại corpus PDF thật do dữ liệu không có tại máy.

## Changes Made

| File hoặc sản phẩm | Tóm tắt thay đổi | Task ID |
|---|---|---|
| `src/app/rag/parse_docling.py` | Bỏ ngưỡng 50% và tập số toàn trang. Chỉ xem một bảng đã đủ khi mỗi dòng gốc có nhãn và đủ số liệu cùng nằm trên một dòng tương ứng trong một bảng ứng viên, giữ nguyên vị trí cột. Chuẩn hóa dấu/chữ hoa của nhãn; mỗi dòng ứng viên chỉ được ghép một lần. | T-006 |
| `src/app/rag/parse_docling.py` | Đếm số liệu bằng Counter và giữ dấu thập phân, không đánh đồng `1.5%` với `15%`. Khi thiếu dòng, giữ nội dung bản ảnh và gắn bảng gốc, không quay lại toàn bộ trang chữ rác. | T-006 |
| `tests/unit/test_parse_docling_table_coverage.py` | Mười test không cần model: mất nửa bảng, tỷ lệ trùng trong đoạn văn/bảng khác, bản đủ có dấu không bị lặp, dịch vụ trùng tỷ lệ, dòng trùng, tráo mức phí giữa dịch vụ/cột, hai kiểu tỷ lệ thập phân. | T-006 |
| `tests/unit/test_parse_docling_repair.py` | Sửa test trước đây chấp nhận mất dòng Vùng II để yêu cầu giữ lại bảng có dòng bị mất. | T-006 |

## Related Files

- **Task Records**: `.agent/execution/tasks/T-006.md`, `.agent/planning/epics.md`.
- **Context Packages**: Phạm vi review và yêu cầu sửa PR #30; [bình luận review](https://github.com/caitoithap/bank-assistant/pull/30#issuecomment-6461848862).
- **Task Board**: `.agent/execution/task-board.md` (giữ trạng thái cũ).
- **Current Context**: `.agent/execution/current-context.md` (không sửa trạng thái chung).
- **Decisions**: `DEC-001`.
- **Change Requests**: `CR-006`, `CR-007` — sửa lỗi trong phạm vi parser hiện tại.
- **Risks or Blockers**: Xem giới hạn bên dưới.
- **Review Request**: Reviewer độc lập tiếp theo của PR #30; Codex không tự approve bản sửa này.
- **Commits**: `4e9c5a7117b5aa22405211f1625d13dbe92e06d8` (code và test), sau base `43e736f`; commit báo cáo bổ sung được truy vết qua PR #30.

## Command Evidence

| Lệnh | Kết quả | Bằng chứng |
|---|---|---|
| `agent task start T-006` | not-run | Task đã terminal trong PR; sửa finding theo yêu cầu trực tiếp của người dùng, không mở lại trạng thái bằng tay. |
| `agent task verify T-006` | not-run | Chạy kiểm tra trực tiếp được ghi ở dưới; không sửa report cũ. |
| `agent task report T-006` | not-run | Tạo báo cáo bổ sung thay cho ghi đè báo cáo cuối. |
| `agent review request T-006` | not-run | Không ghi đè review cuối hoặc tự duyệt; chuyển bản sửa qua PR đang mở. |

## Verification Evidence

| Kiểm tra | Kết quả | Bằng chứng |
|---|---|---|
| Test hồi quy mới chạy với parser tại `43e736f` | passed | Phát hiện lỗi như kỳ vọng: 9 failed, 1 passed. Dùng `-o pythonpath` để nạp parser cũ, không chỉnh sửa checkout cũ. |
| `python -m pytest tests/unit/test_parse_docling.py tests/unit/test_parse_docling_repair.py tests/unit/test_parse_docling_table_coverage.py -q -p no:cacheprovider` | passed | 31 passed, 1 skipped; test bị skip dùng Tesseract giả dưới dạng script POSIX. Python 3.13.15 Windows, docling 2.143.0, docling-core 2.105.0, torch 2.14.1+cpu. Môi trường riêng cài thành công từ requirements-dev.txt. |
| `ruff check .` | passed | All checks passed. |
| `python scripts/validate-framework.py` | passed | FRAMEWORK_VALIDATION_PASS trong checkout riêng của bản sửa. |
| `python -m pytest -q -p no:cacheprovider` | failed | Windows fatal exception: access violation tại logging.LogRecord.__init__, từ tests/api/test_request_logging.py:61. Trùng vị trí lỗi native Windows đã ghi trong ISSUE-011; không coi toàn bộ suite Windows là đạt. |
| CI Linux tại commit mới | not-run | Chờ CI tự chạy sau push; kết quả hiển thị ở tab Checks PR #30. Không dùng kết quả CI của commit cũ làm bằng chứng cho bản sửa này. |
| Integration và corpus PDF thật | not-run | Không có Tesseract tại máy và không có corpus thật. Không tuyên bố đã chạy lại model/corpus. |

## Deviations

- **Plan Deviations**: Sửa finding trong PR #30 chưa merge theo yêu cầu người dùng; giữ nguyên task terminal và báo cáo cuối, không tự phê duyệt thay đổi.
- **Approved By**: Yêu cầu trực tiếp của người dùng trong phiên này: “resolve luôn đi”. Không phải bằng chứng review độc lập đã approve.
- **Known Limitations**: Đối chiếu bảo thủ có thể gắn thêm bảng gốc nếu OCR sửa chữ ngoài việc thêm dấu, đổi cách nhóm số hoặc tách/gộp dòng/cột; bảng gốc có thể không dấu và trùng một phần với bản ảnh. Cách này giữ bản ảnh đọc tốt và bảo toàn dữ liệu đã có, thay vì âm thầm bỏ dòng. Bộ lọc trang quá rác, bảng không có số liệu được nhận diện, và bảng nhiễu vẫn giữ nguyên; số nguyên ngắn không có dấu % vẫn là giới hạn đã nêu trong report trước. Chưa đánh giá tần suất bảng bổ sung trên corpus thật. Full suite Windows gặp lỗi logging đã ghi ở ISSUE-011; cần CI Linux để xác nhận toàn bộ suite.

## Completion Criteria

- [x] Thay đổi ánh xạ tới T-006 và finding PR30-F03.
- [x] Có test thể hiện lỗi trên bản cũ và đạt trên bản sửa.
- [x] Sai lệch và giới hạn được ghi rõ.
- [x] Hoàn tất chạy kiểm tra cục bộ và ghi rõ kết quả đạt/không đạt trước khi push; CI mới chờ kích hoạt khi push.
- [x] Bàn giao review độc lập, không tự approve.
- [x] Bổ sung hash commit code vào task-commit-map trong commit tài liệu đi kèm.

## Forbidden Actions

Không dùng báo cáo này thay cho review độc lập hoặc khẳng định đã kiểm chứng model/corpus khi chưa chạy. Giữ nguyên báo cáo lịch sử.

## Output Requirements

Báo cáo bổ sung và code/test được đưa lên PR #30, giữ nguyên API đầu ra parser.
