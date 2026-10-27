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

Ghi chú định dạng: đây là checklist review tài liệu của A (không theo `review-report-template.md`, vốn dành cho review task của Reviewer Agent); review độc lập của task nằm ở `.agent/reports/review/T-001.md`.

Bằng chứng phần việc chính của T-001: A (trong-hung) tự đọc ba tài liệu baseline và ghi kết luận cho từng tài liệu. File này trả lời comment của B trên PR #29 (điểm 1: thiếu bằng chứng A đã review).

Cách dùng: với mỗi tài liệu, A đọc tài liệu gốc, tick các mục đã kiểm, đánh giá các **quan sát của executor** (đồng ý / không đồng ý / bỏ qua) và chọn phương án (ví dụ "đồng ý, chọn (a)"), rồi viết **kết luận của A** bằng lời của mình. Các quan sát và cột **Phương án đề xuất** chỉ là phân tích của executor `claude-code-a` (phương án in đậm là phương án executor khuyên dùng), không phải kết luận của A, và không thay cho việc A tự đọc.

## Record Metadata

- **Report ID**: `T-001-A-baseline`
- **Title**: `Checklist review baseline của A cho T-001`
- **Owner**: `trong-hung`
- **Reviewer**: `trong-hung`
- **Executor**: `claude-code-a`
- **Status**: `approved`
- **Review Type**: `documentation`
- **Task ID**: `T-001`
- **Report Date**: `2026-10-27`

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

- [x] Mục tiêu và phạm vi (bao gồm / không bao gồm) đúng với ý định sản phẩm.
- [x] Bốn nhóm người dùng (nhân viên, người duyệt, vận hành, tích hợp) đủ và đúng.
- [x] FR-01..FR-12: mỗi FR có tiêu chí chấp nhận kiểm chứng được.
- [x] NFR-01..NFR-10: ngưỡng có số và có cách đo.
- [x] Giả định và ràng buộc (CPU, 15 GB RAM, Gemini free tier, 10 ngày) thực tế.

### Quan sát của executor (A đánh giá từng dòng)

| # | Quan sát | Phương án đề xuất (của executor) | A đánh giá |
|---|---|---|---|
| S-1 | Trường `Authority` vẫn ghi `draft — pending approval in DEC-001` dù DEC-001 đã `accepted`; contract và kiến trúc cũng vậy. Nên cập nhật thành đã duyệt (sửa trạng thái, không đổi nội dung). | **(a) Đề xuất:** sửa `Authority` của 3 tài liệu thành `approved — DEC-001 (PR #1)` trong một PR docs nhỏ; chỉ đổi trạng thái nên chỉ đổi trạng thái; gộp vào CR-002 để B duyệt cùng các mục SRS khác. (b) Để nguyên, ghi chú trong DEC-001 — dễ gây hiểu nhầm cho người đọc sau. | Đồng ý, chọn phương án in đậm → CR-002 |
| S-2 | RBAC chỉ theo `department`; SRS không nói ai được xem tài liệu `confidential` trong cùng phòng. Hiện nhân viên `credit` sẽ thấy mọi tài liệu `credit` kể cả `confidential`. Có đúng ý định không? | (a) Giữ như hiện tại: cùng phòng thì xem được mọi tài liệu của phòng, `confidential` chỉ ảnh hưởng routing (đơn giản, đủ cho MVP). (b) Thêm quy tắc: chỉ role `approver` xem `confidential` — cần CR (đổi SRS + kiến trúc) và thêm test. **Đề xuất (a)**, ghi rõ vào SRS khi sửa S-1 để không còn mơ hồ. | Đồng ý, chọn phương án in đậm → CR-002 |
| S-3 | FR-04 ghi "input nhạy cảm route sang local" nhưng không định nghĩa "nhạy cảm" (PII? classification nào?). Kiến trúc định nghĩa (PII hoặc `confidential`), SRS thì chưa. | **(a) Đề xuất:** định nghĩa trong SRS: "nhạy cảm = câu hỏi có PII sau khi che, hoặc có chunk `confidential` trong context, hoặc `force_local=true`" — khớp kiến trúc. Là làm rõ, không đổi hành vi, nhưng sửa SRS đã duyệt nên đi qua CR nhỏ (gộp với S-2). (b) Để kiến trúc làm nguồn định nghĩa, SRS trỏ sang. | Đồng ý, chọn phương án in đậm → CR-002 |
| S-4 | NFR-08 (p95 < 10 s) chỉ đo "với Gemini"; route local không có ngưỡng (RISK-002 đã ghi nhận). Chấp nhận được cho MVP? | **(a) Đề xuất:** chấp nhận cho MVP, ghi trong SRS "NFR-08 chỉ áp dụng route cloud; route local đo và báo cáo, không có ngưỡng" (RISK-002 đã theo dõi). (b) Đặt ngưỡng local, ví dụ p95 < 60 s — dễ không đạt trên CPU. | Đồng ý, chọn phương án in đậm → CR-002 |
| S-5 | Không có NFR cho thời gian chờ trong hàng (FR-09/FR-10 chỉ yêu cầu đo). | **(a) Đề xuất:** không thêm NFR; E-013 vẫn đo thời gian chờ và báo cáo trong release v1.0. (b) Thêm NFR, ví dụ p95 chờ < 30 s khi burst 30 job — cần CR và test tải, tốn thời gian. | Đồng ý, chọn phương án in đậm → không cần việc (giữ nguyên SRS) |

### Kết luận của A cho SRS

- **Đã đọc**: có
- **Kết luận**: đồng ý
- **Finding mới của A**: không có ngoài các quan sát trên

## 2. Contract — `docs/04-api/contract.md` + `openapi.yaml` + `src/app/contracts.py`

### Mục cần kiểm

- [x] Bảng endpoint khớp `paths` trong `openapi.yaml`.
- [x] Quy tắc lỗi (400/401/403/404/409/429/503) khớp response khai báo trong OpenAPI.
- [x] Hợp đồng nội bộ (`LLM`, `Retriever`, `Answerer`, `Masker`, `User`) đủ để A và B làm song song.
- [x] Quy tắc versioning và kiểm soát thay đổi rõ ràng.

### Quan sát của executor (A đánh giá từng dòng)

| # | Quan sát | Phương án đề xuất (của executor) | A đánh giá |
|---|---|---|---|
| C-1 | `top_k`, `force_local` không truyền được xuống `Answerer` (F-01 của B, ISSUE-002). | **(a) Đề xuất:** thêm `top_k: int = 5, force_local: bool = False` vào `Answerer.answer()` (và payload job), qua PR `contract` cả hai duyệt, làm trước T-019. (b) Gom thành dataclass `AskOptions(top_k, mode, force_local)` truyền một tham số — gọn hơn khi thêm tuỳ chọn sau này nhưng sửa nhiều chỗ hơn. | Đồng ý, chọn phương án in đậm → CR-003, ISSUE-002 |
| C-2 | `Retriever.retrieve(question, user, k)` trong `contracts.py:70` không có tham số `mode`, nhưng T-016 ghi `retrieve(question, user, k, mode)`. Hợp đồng và task lệch nhau; cần chốt trước T-016 (có thể gộp vào ISSUE-002). | **(a) Đề xuất:** thêm `mode: RetrievalMode = "hybrid_rerank"` vào `Retriever.retrieve()`, gộp vào cùng PR `contract` với C-1 (ISSUE-002). (b) Bỏ `mode` khỏi T-016, để `Answerer` chọn retriever theo mode — cần sửa task T-016 qua CR. | Đồng ý, chọn phương án in đậm → CR-003, ISSUE-002 |
| C-3 | Contract nói lỗi body là `400`, nhưng không path nào trong OpenAPI khai báo `400`; FastAPI mặc định trả `422`. T-004 sẽ thêm handler, nhưng OpenAPI cũng cần khai báo. | **(a) Đề xuất:** giữ `400` như contract; T-004 thêm handler đổi lỗi validation 422 → 400 với định dạng lỗi chung, và bổ sung `400` vào các path trong `openapi.yaml` (PR `contract`). (b) Đổi contract sang `422` theo mặc định FastAPI — ít code hơn nhưng phải sửa contract đã duyệt và n8n phải xử lý 422. | Đồng ý, chọn phương án in đậm → CR-003 |
| C-4 | `403` (RBAC/role) chỉ khai báo cho `/agent/{thread_id}/decision`. Với `/ask`, RBAC là filter nên không trả 403 — hợp lý, nhưng contract nên nói rõ. | **(a) Đề xuất:** thêm một câu vào contract: "RBAC ở `/ask` là filter: tài liệu không có quyền coi như không tồn tại, trả từ chối chứ không trả 403". Làm rõ, gộp vào PR `contract`. (b) Để nguyên. | Đồng ý, chọn phương án in đậm → CR-003 |
| C-5 | `/feedback` nhận bất kỳ `trace_id`; chưa nói user có được chấm điểm trace của người khác không. `/chat` không trả `trace_id` nên không gửi feedback cho `/chat` được. | **(a) Đề xuất:** quy tắc "chỉ chủ của trace mới gửi feedback" (404 nếu không phải); thêm `trace_id` vào `ChatResponse` để `/chat` cũng có feedback. Gộp vào PR `contract`, làm ở E-013. (b) Cho mọi user chấm mọi trace — đơn giản nhưng ảnh hưởng chất lượng số liệu. | Đồng ý, chọn phương án in đậm → CR-003 |
| C-6 | `/agent` không có quy tắc sở hữu thread (F-04 của B, ISSUE-005). | **(a) Đề xuất (theo ISSUE-005):** thread thuộc người tạo; chỉ người tạo đọc/tiếp tục; `approver` chỉ duyệt thread cùng department; tra giao dịch chỉ trong tài khoản gắn với department của user. Chốt ở contract trước khi bắt đầu E-011 (M-002). (b) Approver duyệt mọi thread — đơn giản nhưng rộng quyền. | Đồng ý, chọn phương án in đậm → ISSUE-005 |

### Kết luận của A cho contract

- **Đã đọc**: có
- **Kết luận**: đồng ý
- **Finding mới của A**: không có ngoài các quan sát trên

## 3. Kiến trúc — `docs/02-architecture/architecture.md`

### Mục cần kiểm

- [x] Sơ đồ thành phần và bảng trách nhiệm khớp phân công A/B.
- [x] Luồng dữ liệu: che PII trước log/trace/hàng chờ/LLM cloud.
- [x] RBAC áp trong truy vấn Qdrant, không lọc sau.
- [x] Topology compose và cổng hợp lý, chỉ bind `127.0.0.1`.
- [x] Các quyết định chính đã/ sẽ có decision record.

### Quan sát của executor (A đánh giá từng dòng)

| # | Quan sát | Phương án đề xuất (của executor) | A đánh giá |
|---|---|---|---|
| A-1 | Payload job chỉ có câu hỏi đã che + `user_id`; mất tín hiệu routing và cách lấy lại quyền (F-02 của B, ISSUE-003). | **(a) Đề xuất (theo ISSUE-003):** payload job thêm `pii_types: list[str]` (chỉ tên loại, không có giá trị) và `force_local`; worker phân giải `User` lại từ `user_id` qua kho key (không tin dữ liệu trong payload). Làm trong T-024/T-025. (b) Route ngay ở API rồi đưa `route` vào payload — đơn giản nhưng không tính được classification của chunk (chỉ biết sau retrieval). | Đồng ý, chọn phương án in đậm → ISSUE-003 |
| A-2 | Filter retrieval chỉ có department + superseded; routing nhạy cảm ở M-002 (F-03 của B; đề xuất xử lý: DEC-006 + CR-001). | Đã có hướng: **DEC-006 + CR-001** (M-001 chỉ dùng tài liệu `public`, rollback giữ giới hạn). Việc còn lại: A và B duyệt CR-001. | Đồng ý → CR-001 |
| A-3 | Judge RAGAS là Gemini (cloud): khi eval, câu hỏi + context được gửi lên cloud. M-001 chỉ dùng tài liệu `public` nên ổn; từ M-002 eval trên tài liệu `confidential` sẽ đẩy chunk mật lên cloud qua judge. Cần quy tắc cho E-008/E-014. | **(a) Đề xuất:** quy tắc cho eval: judge cloud chỉ nhận câu hỏi/context `public`; câu hỏi dùng tài liệu `internal`/`confidential` chấm bằng judge local (Qwen) hoặc chỉ đo chỉ số không cần LLM (hit@5, refusal). Ghi vào DEC mới hoặc phạm vi E-014. (b) Chấp nhận vì tài liệu là bản công khai/dữ liệu tổng hợp (SRS loại trừ dữ liệu thật) — đơn giản, nhưng trái tinh thần "chunk mật không lên cloud". | Đồng ý, chọn phương án in đậm → ISSUE-006 |
| A-4 | `data/audit.db` (SQLite) có thể được ghi từ cả `api` và `worker`; cần chốt process nào ghi audit cho job, tránh khoá ghi đồng thời. | **(a) Đề xuất:** chỉ API ghi audit (lúc nhận job và lúc trả kết quả); worker không ghi. Bật WAL cho SQLite. Ghi vào T-015/T-024. (b) Cả hai cùng ghi với WAL + retry khi khoá — chạy được nhưng dễ trùng/thiếu dòng. | Đồng ý, chọn phương án in đậm → ISSUE-007 |
| A-5 | Mục "Các quyết định chính" nhắc 4 ADR (Qdrant hybrid, routing lai, RBAC payload filter, RQ) nhưng chưa có decision record nào cho chúng (DEC-001..006 là quyết định quy trình). FR-12 yêu cầu ADR, nên có thể để tới E-016. | **(a) Đề xuất:** viết 4 decision record ADR (Qdrant hybrid, routing lai, RBAC payload filter, RQ) ở E-016 như FR-12 yêu cầu; tạo issue nhắc việc ngay bây giờ. (b) Viết ngay trong tuần 1 — tốn thời gian khi chưa có code chứng minh. | Đồng ý, chọn phương án in đậm → ISSUE-008 |
| A-6 | Model embedding và nơi chạy: bge-m3 có "yếu" không, có nên dùng Qwen3-Embedding hoặc GPU Kaggle/Colab? Máy A: Ryzen 7 5800H 8C/16T, RAM 15 GB (đã thêm swap 8 GB), GPU AMD không dùng được cho PyTorch; model embedding phải chạy CPU local vì mỗi câu hỏi phải embed bằng đúng model đã index. | Executor đề xuất: giữ bge-m3 (dense + sparse, vừa RAM, không cần CR); chỉ dùng Kaggle nếu ingest trên CPU > 60 phút (ngưỡng RISK-002). | **Quyết định của A (2026-10-27): chạy toàn bộ trên local, không dùng Kaggle/Colab; giữ bge-m3.** → không đổi baseline; ngưỡng RISK-002 giữ nguyên |

### Kết luận của A cho kiến trúc

- **Đã đọc**: có
- **Kết luận**: đồng ý
- **Finding mới của A**: không có ngoài các quan sát trên

## Kết luận chung của A

- **Quyết định của A về baseline**: giữ duyệt kèm follow-up
- **Những quan sát A đồng ý cần theo dõi**: tất cả, theo phương án in đậm; theo dõi ở CR-001, CR-002, CR-003, ISSUE-002, ISSUE-003, ISSUE-005, ISSUE-006, ISSUE-007, ISSUE-008 (S-5 và A-6 không cần việc)
- **Ngày**: `2026-10-27`
- **Nguồn**: A xác nhận trong chat với executor ngày 2026-10-27: "đã đọc và đồng ý", đồng ý cả phương án đề xuất (in đậm); quyết định A-6 (chạy toàn bộ local, không Kaggle) cùng ngày. Executor ghi lại nguyên ý, không thêm kết luận.
- **Xác nhận trên GitHub**: [https://github.com/caitoithap/bank-assistant/pull/29#issuecomment-6433702231](https://github.com/caitoithap/bank-assistant/pull/29#issuecomment-6433702231) — comment trên PR #29 từ tài khoản `caitoithap` (A), đăng qua Claude Code theo yêu cầu của A.

## Completion Criteria

- [x] A đã đọc cả ba tài liệu và xác nhận kết luận: xác nhận trong chat với executor (2026-10-27), sau đó xác nhận trên PR #29 bằng tài khoản của A. Phần đánh giá từng dòng do executor ghi theo xác nhận chung đó ("đồng ý, chọn phương án in đậm").
- [x] Mỗi quan sát của executor có đánh giá của A.
- [x] Các điểm A đồng ý cần theo dõi đã có issue hoặc change request.
- [x] Trạng thái chuyển sang `approved` (A giữ duyệt) hoặc `changes-required` (A thấy cần sửa baseline).

## Forbidden Actions

- Executor không tự đưa ra đánh giá hay kết luận thay cho A; chỉ được ghi lại đúng nội dung A đã xác nhận, kèm nguồn.
- Không coi việc PR #1 đã merge là bằng chứng A đã đọc.

## Output Requirements

- Lưu tại `.agent/reports/review/T-001-A-baseline.md`, liên kết từ implementation report của T-001.
