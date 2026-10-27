---
id: assessment-t-002-platform-contract
title: "T-002: đánh giá contract và fakes cho nền tảng"
type: report
domain: contract
module: src/app/contracts.py
tags: [assessment, t-002, auth, queue, n8n, fakes]
priority: 2
---
# T-002: đánh giá contract và fakes cho nền tảng

## Scope and Evidence

- **Owner**: `teammate-b`
- **Author**: `codex` (executor; không phải review độc lập của task)
- **Status**: `complete`
- **Date**: `2026-10-27`
- **Baseline**: `529e86e92dbaea1ccb66a5bcc7bac9a1067500ff`, PR #29 đã merge, T-001 done, E-001 EPIC_IN_PROGRESS.
- **Task**: `.agent/execution/tasks/T-002.md`; issue https://github.com/caitoithap/bank-assistant/issues/3.
- **Inputs**: `src/app/contracts.py`, `schemas.py`, `main.py`, `deps.py`, `fakes_runtime.py`; `tests/fakes.py`, `tests/unit/test_fakes.py`, `tests/api/test_ask_fake.py`; `docs/04-api/contract.md`, `openapi.yaml`, `docs/05-database/schema.md`, `docs/06-security/security-design.md`, `docs/11-integrations/n8n.md`, `docs/13-observability/observability.md`; tasks T-013..015, T-020..021, T-024..025; CR-003/004, ISSUE-002/003/005/007/009.

## Platform Compatibility Matrix

| Nhu cầu B | Bằng chứng hiện tại | Kết luận | Theo dõi / hành động |
|---|---|---|---|
| Auth: key → user_id/department/role | `User` có đủ ba trường; `FakeRetriever` lọc theo department + public. `get_current_user` hiện là stub và có thể override bằng dependency FastAPI. | Đủ hình dạng dữ liệu cho T-014; fake không chứng minh key hashing/401/403. | T-014 triển khai auth và test thực; không thêm raw key vào User. |
| Truyền tùy chọn `/ask` | `AskRequest` nhận top_k/mode/force_local; `Answerer.answer` chỉ nhận question/user/mode; `FakeAnswerer` cố định k=5 và route cloud. | Chưa đủ; ép local/top_k bị mất. | ISSUE-002 + CR-003 C-1 đã đề xuất; không tạo CR trùng. Cập nhật FakeAnswerer và CannedAnswerer cùng PR áp dụng CR. |
| Retrieval mode và quyền | `Retriever.retrieve` chưa nhận mode; fake chỉ lọc department, không mô phỏng superseded/classification gate. | Mode thiếu theo T-016; fake chỉ là kiểm tra cơ bản. | CR-003 C-2; CR-001/T-016 cần test Qdrant filter thật, không coi fake filter là bằng chứng RBAC trong query hoặc không lộ tài liệu mật. |
| Queue: tùy chọn, PII, quyền hiện hành | Redis baseline chỉ có masked question + user_id; không có envelope/fake resolver để round-trip request và phân giải lại quyền. | Cần giao diện nội bộ rõ cho API/worker/auth. | ISSUE-003; CR-005 Q-1/Q-2 cụ thể hóa envelope và resolver, kết hợp CR-003. |
| Queue: retry/backoff 429 | `LLM.chat` có success result nhưng không định nghĩa lỗi status/retry_after. `FakeLLM(reply)` luôn thành công; không cấu hình chuỗi 429 → thành công như AC T-025 yêu cầu. | Chưa đủ cho worker và regression test backoff. | CR-005 Q-3/Q-4: lỗi chuẩn hóa đã làm sạch và scripted fake; T-013/T-025 áp dụng sau duyệt. |
| n8n: intake → classify → enqueue → Wait/poll → reply | OpenAPI có ChatResponse(intent/needs_human), JobAccepted, JobStatus và 404 owner-only; key dịch vụ department public. Chưa có `/chat`/queue fake HTTP trong scaffold. | HTTP shape đủ cho flow ở mức thiết kế; chưa chứng nhận workflow chạy. | E-012 dùng cùng user_id dịch vụ khi POST/GET; không mở API mới chỉ để fake workflow. CR-003 xử lý lỗi 400; test n8n ở E-012. |
| Audit/trace/feedback | AskResult có trace_id nullable, LLMResult có token/meta; không có completion-event contract hay tracing cho fake. | Không đủ để tuyên bố audit/chi phí đã hoạt động. | CR-004 + ISSUE-007 cho event/consumer; E-013 cho cost/span/feedback (CR-003 C-5). Không dùng token=0 của fake làm phép đo thực. |
| PII | Masker trả masked text và danh sách loại; FakeMasker chỉ che CCCD 12 số. | Đủ tuple shape, không đủ bảo đảm PII điện thoại/tài khoản/log/output. | T-020/021 kiểm soát PII thực; ISSUE-003 + CR-003 giữ tín hiệu trước che, force_local luôn được tôn trọng. |

## Findings and Disposition

| ID | Severity | Finding | Required Action | Owner |
|---|---|---|---|---|
| `T002-F01` | `major` | Request top_k/force_local và retrieval mode chưa đi qua giao diện/fake. | Áp dụng CR-003 sau duyệt; cập nhật tất cả implementation/fake/caller và regression tests trong cùng PR. | A + B |
| `T002-F02` | `major` | Chưa định nghĩa đầy đủ envelope an toàn và cách worker lấy lại User có thẩm quyền; không được tin department/role trong payload. | CR-005 Q-1/Q-2 cụ thể hóa ISSUE-003; test revocation/department change và owner-only poll bằng user_id hiện hành. | B (queue/auth), A (Answerer) |
| `T002-F03` | `major` | Worker không có lỗi 429 chuẩn hóa/Retry-After; FakeLLM hiện không tạo được kịch bản AC T-025. | CR-005 Q-3/Q-4 định nghĩa lỗi và scripted fake trước T-013/T-025. | B |
| `T002-F04` | `minor` | FakeMasker/department filter chỉ mô phỏng phần nhỏ của chính sách; thiếu HTTP fake cho endpoint chưa triển khai. | Ghi rõ giới hạn, kiểm chứng tại T-014/T-016/T-020/T-021/T-024 và E-012; không coi scaffold là runtime an toàn. | A + B theo task |

## Verification

- `python -m pytest -q tests/api tests/unit`: **7 passed** trên Windows, baseline 529e86e.
- `python -m ruff check .`: **All checks passed**.
- Bộ framework đầy đủ trên Windows có lỗi POSIX/cp1252 đã biết, ISSUE-009; không đánh dấu các lỗi đó pass. T-002 dùng CI Linux để kiểm tra toàn bộ ba bước tương đương `make check` trước khi bàn giao review.
- Không sửa `contracts.py`, fakes, OpenAPI hay tài liệu baseline trong T-002; chỉ đánh giá và tạo CR. Các test mô tả behavior tương lai trong CR-005 chưa được chạy, vì chưa triển khai.

## Written Conclusion

**Chưa xác nhận OK vô điều kiện cho toàn bộ nền tảng.** Shape User, Masker, LLMResult và các HTTP response dự kiến đủ cho scaffold; có các gap cần CR-003, CR-004 và **CR-005 mới**. Acceptance criterion T-002 cho phép "written OK hoặc CR filed"; task đáp ứng theo nhánh **CR filed**, không yêu cầu hiện thực mọi CR ngay trong task review này.

Việc assessment hoàn thành không giải quyết các finding runtime, không phê duyệt CR và không thay cho review độc lập của task tại `.agent/reports/review/T-002.md`.
