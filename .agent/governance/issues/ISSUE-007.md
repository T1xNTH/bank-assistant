---
id: issue-007
title: "ISSUE-007: Chốt một process duy nhất ghi audit.db"
type: governance
domain: governance
module: issues
tags: [issue, t-001, review-observation, a-4]
priority: 2
---
# ISSUE-007: Chốt một process duy nhất ghi audit.db

## Usage Purpose

Theo dõi quan sát A-4 trong review baseline của A (`.agent/reports/review/T-001-A-baseline.md`). A đã đồng ý và chọn phương án ngày 2026-10-27. Review follow-up của B thay đề xuất chỉ ghi audit khi API trả kết quả bằng consumer độc lập qua Redis Stream; nguồn: [comment PR #29](https://github.com/caitoithap/bank-assistant/pull/29#issuecomment-6434139388). Lựa chọn ban đầu của A được giữ trong report lịch sử; thay đổi kiến trúc cần A và B duyệt CR-004 trước khi hiện thực.

## Record Metadata

- **Issue ID**: `ISSUE-007`
- **Title**: `Chốt một process duy nhất ghi audit.db`
- **Owner**: `teammate-b`
- **Reporter**: `claude-code-a`
- **Status**: `triaged`
- **Issue Type**: `gap`
- **Priority**: `3`
- **Created Date**: `2026-10-27`
- **Target Date**: `2026-10-30`

## Description

`data/audit.db` (SQLite) có thể được ghi từ cả `api` và `worker`. Kiến trúc chưa nói process nào ghi audit cho job. Đề xuất chỉ API ghi lúc nhận job và lúc trả kết quả chưa đủ: client không poll hoặc kết quả hết TTL thì không ghi được thông tin hoàn tất; poll lặp lại có thể tạo trùng.

## Impact

- **Affected Scope**: `data/audit.db, src/app/security/audit.py, src/app/queue/`
- **Severity**: `medium`
- **User or Delivery Impact**: `ghi đồng thời từ api và worker có thể khoá SQLite hoặc trùng/thiếu dòng audit`

## Reproduction Evidence

- **Preconditions**: `main tại 0cbf93a`
- **Steps**: `đọc các tài liệu trong Affected Scope`
- **Observed Result**: `như phần Description`
- **Expected Result**: `consumer riêng là nơi duy nhất ghi SQLite; worker phát sự kiện hoàn tất qua Redis Stream; audit không phụ thuộc polling, không trùng khi replay và không chứa PII gốc; SQLite bật WAL`
- **Evidence Paths**: `.agent/reports/review/T-001-A-baseline.md, .agent/reports/review/PR-029-B-followup.md`

## Related Files

- **Affected Files**: `data/audit.db, src/app/security/audit.py, src/app/queue/`
- **Tasks or Epics**: `E-006 (T-015), E-009 (T-024)`
- **Decisions**: `none`
- **Risks**: `none`
- **Blockers**: `none`
- **Change Requests**: `.agent/governance/change-requests/CR-004.md` (`proposed`)

## Acceptance Criteria

- [x] Nguyên nhân gốc hoặc hướng xử lý đã được ghi lại.
- [ ] Kết quả khắc phục được định nghĩa bằng điều kiện quan sát được.
- [ ] Cách kiểm tra regression được định nghĩa khi cần.

Các điều kiện sau là yêu cầu cho implementation sau khi CR-004 được duyệt, chưa phải kết quả đã kiểm chứng:

- [ ] API phát sự kiện tiếp nhận request/job đã che; worker phát `job.completed` hoặc `job.failed` khi kết thúc cuối cùng, không ghi trực tiếp SQLite.
- [ ] Một audit consumer ghi transaction SQLite, commit trước ACK. Khóa duy nhất `(job_id, event_type)` chống trùng sự kiện vòng đời job; audit HTTP dùng request ID riêng để không gộp các request polling khác nhau.
- [ ] Lưu kết quả cuối cùng và phát sự kiện hoàn tất nguyên tử trong Redis; kiểm chứng với cách lưu kết quả của RQ, không giả định hook thông thường đã đủ.
- [ ] Stream có persistence và retention riêng; không xóa sự kiện chưa xử lý theo TTL kết quả. Consumer phục hồi pending events khi khởi động lại.
- [ ] Job không được poll vẫn có audit hoàn tất; poll nhiều lần và kết quả hết TTL không làm mất hoặc nhân đôi audit vòng đời job.
- [ ] Consumer chết sau commit trước ACK rồi replay không tạo trùng; consumer restart xử lý được pending events.
- [ ] Lỗi giữa lưu kết quả và phát sự kiện không để lại kết quả cuối cùng thiếu sự kiện; retry không phát thất bại cuối cùng sai thời điểm, thất bại cuối cùng vẫn có audit.
- [ ] Sự kiện có `job_id`, trạng thái, route, refused, latency, chi phí, `trace_id` khi có; payload, Stream và SQLite không chứa PII gốc.

## Resolution

- **Resolution Type**: `not-applicable`
- **Resolution Summary**: `B chấp nhận phương án follow-up: worker phát sự kiện Redis Stream, consumer riêng ghi SQLite/WAL, commit trước ACK, chống trùng và phục hồi pending; độc lập polling. CR-004 proposed chờ A và B duyệt trước khi đồng bộ T-015/T-024 và hiện thực; issue vẫn mở.`
- **Verification Evidence**: `none`
- **Resolved By**: `none`
- **Resolved Date**: `none`

## Completion Criteria

- [ ] Acceptance criteria đạt hoặc đã có hướng xử lý được duyệt.
- [ ] Bằng chứng giải quyết đã được liên kết.
- [ ] Các record task, risk, blocker và regression liên quan đã được cập nhật.

## Forbidden Actions

- Không đóng issue khi chưa có bằng chứng giải quyết.
- Không sửa SRS, contract hay kiến trúc đã duyệt khi chưa có change request đã duyệt.

## Output Requirements

- Lưu tại `.agent/governance/issues/ISSUE-007.md`.
- Giữ nguyên mọi heading của issue template.
