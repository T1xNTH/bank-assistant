---
id: review-t-001-a-baseline
title: "T-001: checklist review baseline của A"
type: report
domain: governance
module: execution
tags: [review, baseline, T-001, dec-001]
priority: 1
---
# T-001: checklist review baseline của A (trong-hung)

## Usage Purpose

Bằng chứng phần việc chính của T-001: A (trong-hung) tự đọc ba tài liệu baseline và ghi kết luận cho từng tài liệu. File này trả lời comment của B trên PR #29 (điểm 1: thiếu bằng chứng A đã review).

Cách dùng: với mỗi tài liệu, A đọc tài liệu gốc, tick các mục đã kiểm, đánh giá các **quan sát của executor** (đồng ý / không đồng ý / bỏ qua), rồi viết **kết luận của A** bằng lời của mình. Các quan sát chỉ là phân tích của executor `claude-code-a`, không phải kết luận của A, và không thay cho việc A tự đọc.

## Record Metadata

- **Report ID**: `T-001-A-baseline`
- **Title**: `Checklist review baseline của A cho T-001`
- **Owner**: `trong-hung`
- **Reviewer**: `trong-hung`
- **Executor**: `claude-code-a`
- **Status**: `draft`
- **Review Type**: `documentation`
- **Task ID**: `T-001`
- **Report Date**: `2026-10-26`

## Review Scope

- **Included Artifacts**: `docs/01-business/srs.md`, `docs/04-api/contract.md`, `docs/04-api/openapi.yaml`, `src/app/contracts.py`, `docs/02-architecture/architecture.md` (tại `main` 0cbf93a)
- **Excluded Artifacts**: `các tài liệu domain khác (05-database, 06-security, 12-ai...) chỉ đọc khi cần đối chiếu`
- **Review Standard**: `SRS FR/NFR nhất quán và đo được; contract khớp OpenAPI và contracts.py; kiến trúc thực hiện được FR/NFR và giữ ranh giới tin cậy`

## Related Files

- **Review của B**: `.agent/reports/review/REVIEW-DEC-001-B.md` (F-01..F-04, theo dõi ở ISSUE-002..005)
- **Decision**: `.agent/governance/decisions/DEC-001.md`
- **Implementation Report**: `.agent/reports/implementation/T-001.md`

## 1. SRS — `docs/01-business/srs.md`

### Mục cần kiểm

- [ ] Mục tiêu và phạm vi (bao gồm / không bao gồm) đúng với ý định sản phẩm.
- [ ] Bốn nhóm người dùng (nhân viên, người duyệt, vận hành, tích hợp) đủ và đúng.
- [ ] FR-01..FR-12: mỗi FR có tiêu chí chấp nhận kiểm chứng được.
- [ ] NFR-01..NFR-10: ngưỡng có số và có cách đo.
- [ ] Giả định và ràng buộc (CPU, 15 GB RAM, Gemini free tier, 10 ngày) thực tế.

### Quan sát của executor (A đánh giá từng dòng)

| # | Quan sát | A đánh giá |
|---|---|---|
| S-1 | Trường `Authority` vẫn ghi `draft — pending approval in DEC-001` dù DEC-001 đã `accepted`; contract và kiến trúc cũng vậy. Nên cập nhật thành đã duyệt (sửa trạng thái, không đổi nội dung). | … |
| S-2 | RBAC chỉ theo `department`; SRS không nói ai được xem tài liệu `confidential` trong cùng phòng. Hiện nhân viên `credit` sẽ thấy mọi tài liệu `credit` kể cả `confidential`. Có đúng ý định không? | … |
| S-3 | FR-04 ghi "input nhạy cảm route sang local" nhưng không định nghĩa "nhạy cảm" (PII? classification nào?). Kiến trúc định nghĩa (PII hoặc `confidential`), SRS thì chưa. | … |
| S-4 | NFR-08 (p95 < 10 s) chỉ đo "với Gemini"; route local không có ngưỡng (RISK-002 đã ghi nhận). Chấp nhận được cho MVP? | … |
| S-5 | Không có NFR cho thời gian chờ trong hàng (FR-09/FR-10 chỉ yêu cầu đo). | … |

### Kết luận của A cho SRS

- **Đã đọc**: … (có / chưa)
- **Kết luận**: … (đồng ý / đồng ý kèm điểm cần theo dõi / không đồng ý)
- **Finding mới của A**: … (hoặc "không có")

## 2. Contract — `docs/04-api/contract.md` + `openapi.yaml` + `src/app/contracts.py`

### Mục cần kiểm

- [ ] Bảng endpoint khớp `paths` trong `openapi.yaml`.
- [ ] Quy tắc lỗi (400/401/403/404/409/429/503) khớp response khai báo trong OpenAPI.
- [ ] Hợp đồng nội bộ (`LLM`, `Retriever`, `Answerer`, `Masker`, `User`) đủ để A và B làm song song.
- [ ] Quy tắc versioning và kiểm soát thay đổi rõ ràng.

### Quan sát của executor (A đánh giá từng dòng)

| # | Quan sát | A đánh giá |
|---|---|---|
| C-1 | `top_k`, `force_local` không truyền được xuống `Answerer` (F-01 của B, ISSUE-002). | … |
| C-2 | `Retriever.retrieve(question, user, k)` trong `contracts.py:70` không có tham số `mode`, nhưng T-016 ghi `retrieve(question, user, k, mode)`. Hợp đồng và task lệch nhau; cần chốt trước T-016 (có thể gộp vào ISSUE-002). | … |
| C-3 | Contract nói lỗi body là `400`, nhưng không path nào trong OpenAPI khai báo `400`; FastAPI mặc định trả `422`. T-004 sẽ thêm handler, nhưng OpenAPI cũng cần khai báo. | … |
| C-4 | `403` (RBAC/role) chỉ khai báo cho `/agent/{thread_id}/decision`. Với `/ask`, RBAC là filter nên không trả 403 — hợp lý, nhưng contract nên nói rõ. | … |
| C-5 | `/feedback` nhận bất kỳ `trace_id`; chưa nói user có được chấm điểm trace của người khác không. `/chat` không trả `trace_id` nên không gửi feedback cho `/chat` được. | … |
| C-6 | `/agent` không có quy tắc sở hữu thread (F-04 của B, ISSUE-005). | … |

### Kết luận của A cho contract

- **Đã đọc**: … (có / chưa)
- **Kết luận**: …
- **Finding mới của A**: …

## 3. Kiến trúc — `docs/02-architecture/architecture.md`

### Mục cần kiểm

- [ ] Sơ đồ thành phần và bảng trách nhiệm khớp phân công A/B.
- [ ] Luồng dữ liệu: che PII trước log/trace/hàng chờ/LLM cloud.
- [ ] RBAC áp trong truy vấn Qdrant, không lọc sau.
- [ ] Topology compose và cổng hợp lý, chỉ bind `127.0.0.1`.
- [ ] Các quyết định chính đã/ sẽ có decision record.

### Quan sát của executor (A đánh giá từng dòng)

| # | Quan sát | A đánh giá |
|---|---|---|
| A-1 | Payload job chỉ có câu hỏi đã che + `user_id`; mất tín hiệu routing và cách lấy lại quyền (F-02 của B, ISSUE-003). | … |
| A-2 | Filter retrieval chỉ có department + superseded; routing nhạy cảm ở M-002 (F-03 của B; đề xuất xử lý: DEC-006 + CR-001). | … |
| A-3 | Judge RAGAS là Gemini (cloud): khi eval, câu hỏi + context được gửi lên cloud. M-001 chỉ dùng tài liệu `public` nên ổn; từ M-002 eval trên tài liệu `confidential` sẽ đẩy chunk mật lên cloud qua judge. Cần quy tắc cho E-008/E-014. | … |
| A-4 | `data/audit.db` (SQLite) có thể được ghi từ cả `api` và `worker`; cần chốt process nào ghi audit cho job, tránh khoá ghi đồng thời. | … |
| A-5 | Mục "Các quyết định chính" nhắc 4 ADR (Qdrant hybrid, routing lai, RBAC payload filter, RQ) nhưng chưa có decision record nào cho chúng (DEC-001..006 là quyết định quy trình). FR-12 yêu cầu ADR, nên có thể để tới E-016. | … |

### Kết luận của A cho kiến trúc

- **Đã đọc**: … (có / chưa)
- **Kết luận**: …
- **Finding mới của A**: …

## Kết luận chung của A

- **Quyết định của A về baseline**: … (giữ duyệt / giữ duyệt kèm follow-up / cần change request)
- **Những quan sát A đồng ý cần theo dõi**: … (executor sẽ tạo issue cho các dòng A đánh dấu đồng ý mà chưa có issue)
- **Ngày**: …

## Completion Criteria

- [ ] A đã đọc cả ba tài liệu và ghi kết luận bằng lời của mình.
- [ ] Mỗi quan sát của executor có đánh giá của A.
- [ ] Các điểm A đồng ý cần theo dõi đã có issue hoặc change request.
- [ ] Trạng thái chuyển sang `approved` (A giữ duyệt) hoặc `changes-required` (A thấy cần sửa baseline).

## Forbidden Actions

- Executor không điền phần "A đánh giá" hay "Kết luận của A" thay cho A.
- Không coi việc PR #1 đã merge là bằng chứng A đã đọc.

## Output Requirements

- Lưu tại `.agent/reports/review/T-001-A-baseline.md`, liên kết từ implementation report của T-001.
