---
id: review-pr-029-b-followup
title: "PR #29: xác nhận phương án follow-up sau review của B"
type: report
domain: governance
module: execution
tags: [review, pr-29, t-001, pii, audit]
priority: 2
---
# PR #29: xác nhận phương án follow-up sau review của B

## Review Scope

- **PR**: https://github.com/caitoithap/bank-assistant/pull/29
- **Reviewed Commit**: `c9a8ce6e557e2db7581b0c3b54e17e32c4aee7aa`
- **Task**: `T-001`; đây là review PR, không phải thực thi `T-002`.
- **Reviewer**: `codex`
- **Owner**: `teammate-b` (phía nền tảng, theo ngữ cảnh review)
- **Status**: `approved`
- **Decision Scope**: người dùng chấp nhận phương án follow-up trong report này; không phải phê duyệt toàn bộ PR hoặc change request.
- **Date**: `2026-10-27`
- **Scope**: ghi nhận trao đổi và phương án người dùng chấp nhận; không chứng nhận runtime hoặc thay cho phê duyệt kép các change request.

## Approval Evidence

Sau review, người dùng làm rõ: "1, LLM sẽ không nhìn được dữ liệu nhạy cảm của khách" và yêu cầu "2, đề xuất cơ chế ghi nhận độc lập". Sau khi reviewer giải thích lại điểm PII và đề xuất cơ chế audit qua Redis Stream, người dùng xác nhận: "ok chấp nhận".

Xác nhận này áp dụng cho các phương án dưới đây. Không suy ra việc CR-001, CR-002, CR-003 đã được cả A và B duyệt, PR đã được approve trên GitHub, hoặc task đã hoàn tất.

## Findings and Disposition

### PII: làm rõ finding về routing

- LLM chỉ được nhận văn bản đã che PII đầy đủ; không nhận dữ liệu nhạy cảm gốc của khách hàng. Che cả nội dung context và output theo chính sách hiện hành.
- Finding trước nói về việc bảo toàn tín hiệu PII để đáp ứng quy tắc baseline "input có PII → local"; đó không phải bằng chứng dữ liệu gốc đã bị lộ.
- Nếu cho phép văn bản đã che PII lên cloud, cần ghi rõ ngoại lệ routing trong change request và được duyệt trước khi sửa baseline. Quy tắc `force_local=true` vẫn phải được tôn trọng; giới hạn classification của CR-001 vẫn cần được tuân thủ.
- **Disposition**: người dùng chấp nhận phần làm rõ và hướng xử lý; chưa thay đổi quy tắc routing đã baseline.

### Audit: ghi nhận hoàn tất độc lập với polling

- **Disposition**: người dùng chấp nhận phương án Redis Stream; ISSUE-007 đã được cập nhật, CR-004 được tạo ở trạng thái `proposed` để A và B đồng duyệt trước khi sửa baseline/task/runtime.
- API tạo `job_id`, ghi nhận tiếp nhận và enqueue payload đã che.
- Worker phát sự kiện `job.completed` hoặc `job.failed` khi job kết thúc; retry chưa phải thất bại cuối cùng. Worker không ghi trực tiếp SQLite.
- Sự kiện gồm `job_id`, trạng thái, route, refused, latency, chi phí và `trace_id` khi có; không chứa PII gốc.
- Một audit consumer riêng là nơi duy nhất ghi SQLite. Consumer ghi trong transaction, commit thành công rồi mới ACK Redis Stream.
- Dùng khóa duy nhất `(job_id, event_type)` để replay sự kiện không tạo audit trùng. Audit request HTTP và audit vòng đời job là các sự kiện riêng, không yêu cầu một dòng duy nhất cho cả hai.
- Lưu kết quả cuối cùng và phát sự kiện hoàn tất phải nguyên tử, bằng transaction/script Redis phù hợp với cách lưu kết quả của RQ. Cần kiểm chứng tích hợp RQ trước khi chốt implementation; không giả định hook thông thường đã bảo đảm tính nguyên tử.
- Stream audit có persistence và chính sách lưu riêng; không xóa sự kiện chưa xử lý theo TTL kết quả job. Consumer phục hồi pending events sau khi khởi động lại.
- Consumer không phụ thuộc request GET kết quả. Client không poll, poll nhiều lần hoặc kết quả hết TTL đều không làm mất hay nhân đôi sự kiện audit hoàn tất.

## Required Verification

- Job không được poll vẫn có audit hoàn tất.
- Poll nhiều lần không nhân đôi audit vòng đời job.
- Consumer chết sau commit trước ACK: replay không tạo bản ghi trùng.
- Consumer khởi động lại xử lý được pending events; kết quả hết TTL không xóa sự kiện chưa xử lý.
- Lỗi giữa bước lưu kết quả và phát sự kiện không để lại kết quả cuối cùng thiếu sự kiện tương ứng.
- Retry không phát thất bại cuối cùng sai thời điểm; job thất bại cuối cùng vẫn được audit.
- Không có PII gốc trong payload, Stream hoặc audit; `force_local=true` không chọn cloud.

## Verification Evidence

Kiểm tra trên bản trích xuất riêng của commit được review, không đổi working tree:

- Ruff: pass.
- Framework validator: `FRAMEWORK_VALIDATION_PASS`.
- Pytest trên Windows: `18 passed, 9 failed`; các lỗi liên quan shell POSIX (`true`, `false`, dấu phân cách lệnh) và encoding cp1252. Các file test/runtime liên quan không thay đổi trong PR.
- CI GitHub của PR tại thời điểm review: job `check` thành công.

Kiểm tra bổ sung cho commit tài liệu follow-up: Ruff pass, `FRAMEWORK_VALIDATION_PASS`, `git diff --check` pass. Không chạy lại toàn bộ pytest Windows: không đổi runtime/test; kết quả và giới hạn của lần chạy trên commit gốc được giữ ở trên. CI cho commit mới cần được theo dõi sau push.

## Follow-up

- **B / owner ISSUE-007**: sau khi CR-004 được A và B duyệt, đồng bộ baseline và T-015/T-024/T-025 theo phạm vi được duyệt rồi triển khai cơ chế cùng các kiểm tra đã ghi trong ISSUE-007.
- **A + B**: chốt quy tắc routing PII trong change request nếu muốn khác baseline; không coi xác nhận phương án trong phiên này là đủ phê duyệt kép.
- Kết luận đã đăng tại [comment PR #29](https://github.com/caitoithap/bank-assistant/pull/29#issuecomment-6434139388). Theo yêu cầu tiếp theo của người dùng, commit follow-up cập nhật ISSUE-007, tạo CR-004 và bổ sung làm rõ PII vào CR-002/CR-003 đang `proposed`. CR-003 ghi cách giữ routing hiện hành bằng `effective_force_local = request.force_local OR bool(pii_types)` cho cả API và worker.
- Giữ nguyên report lịch sử đã approved của A và reviewer trước; phần audit mới thay đề xuất follow-up, không viết lại bằng chứng A đã chọn phương án ban đầu. Không chuyển trạng thái T-001 hoặc triển khai task T-002 trong commit này.
- Chưa có runtime implementation hay test cho cơ chế Redis Stream được tuyên bố hoàn thành.
