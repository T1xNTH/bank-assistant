---
id: project-contract
title: API Contract — bank-assistant v0
type: reference
domain: api
module: repository
tags: [contract, api, openapi]
priority: 1
---
# API Contract — bank-assistant v0

## Trạng thái input

- **Status**: `ingested`
- **Authority**: `draft — pending approval in DEC-001`
- **Source Artifact**: `docs/04-api/openapi.yaml`
- **Ingested Date**: `2026-10-24`
- **Validated By**: `trong-hung`, `teammate-b`

## Phạm vi

Contract HTTP bên ngoài của dịch vụ API và các hợp đồng Python nội bộ (`src/app/contracts.py`) giúp hai owner làm song song. Nguồn chuẩn dạng máy đọc được là `docs/04-api/openapi.yaml`; trang này giải thích các quy tắc mà schema không diễn đạt được.

## Endpoints

| Method | Path | Auth | Owner | Tóm tắt |
|---|---|---|---|---|
| GET | `/health` | không | B | Kiểm tra sống (liveness) |
| POST | `/chat` | key | B | Chat tự do với output có cấu trúc (intent, needs_human) |
| POST | `/ask` | key | A | Trả lời RAG đồng bộ kèm trích dẫn |
| POST | `/ask/jobs` | key | B | Đưa một request `/ask` vào hàng chờ → `202 {job_id, position}` |
| GET | `/ask/jobs/{job_id}` | key (chỉ owner) | B | `queued | running | done | failed` + kết quả |
| POST | `/agent` | key | A | Bắt đầu/tiếp tục một agent thread |
| POST | `/agent/{thread_id}/decision` | key, role `approver` | B | Duyệt/từ chối một hành động đang chờ |
| POST | `/feedback` | key | B | 👍/👎 cho một `trace_id` |

## Quy tắc

- **Xác thực**: header `X-API-Key`. Key được lưu dạng hash (`config/api_keys.json`); mỗi key ánh xạ tới `User(user_id, department, role)`.
- **Lỗi**: JSON `{"error": {"code": str, "message": str}}` với
  `400` body không hợp lệ, `401` thiếu/sai key, `403` bị RBAC/role từ chối, `404` không tìm thấy job/thread, `409` quyết định đã được đưa ra, `429` vượt rate limit theo key (kèm `Retry-After`), `503` hàng chờ đầy hoặc dependency bị sập.
- **Từ chối** không phải là lỗi: trả `200` với `found: false` và `answer` = hằng `REFUSAL` (`"Không tìm thấy thông tin này trong tài liệu nội bộ hiện có."`).
- **Trích dẫn**: mọi câu trả lời `found: true` có ≥ 1 trích dẫn `{n, source, page, score}`; `n` khớp với các marker `[n]` trong câu trả lời.
- **PII**: văn bản của request được che trước khi ghi log, ghi trace hay đưa vào hàng chờ; response được che ở đầu ra.
- **Versioning**: thay đổi chỉ thêm (trường optional mới) thì tăng minor của `info.version`; xoá/đổi tên trường hoặc đổi ngữ nghĩa cần change request đã duyệt và tăng major.

## Hợp đồng nội bộ (`src/app/contracts.py`)

| Hợp đồng | Chữ ký | Bên cung cấp | Bên dùng | Fake |
|---|---|---|---|---|
| `LLM` | `chat(messages, alias, temperature=0.0) -> LLMResult` | B (`app/llm.py`) | A (answer, agent) | `tests/fakes.py::FakeLLM` |
| `Retriever` | `retrieve(question, user, k) -> list[Hit]` | A (`app/rag/retrieve.py`) | A answer, B API | `FakeRetriever` |
| `Answerer` | `answer(question, user, mode=None) -> AskResult` | A (`app/rag/answer.py`) | B API + worker | `FakeAnswerer` |
| `Masker` | `mask_text(text) -> tuple[str, list[str]]` | B (`app/security/pii.py`) | A + B | `FakeMasker` |
| `User` | dataclass `user_id, department, role` | B (`app/security/auth.py`) | tất cả | — |

Chọn backend lúc chạy: `RAG_BACKEND=fake|real`, `LLM_BACKEND=fake|litellm`.

## Kiểm soát thay đổi

Mọi thay đổi `openapi.yaml` hay `contracts.py` phải nằm trong PR riêng, gắn label `contract`, được cả hai owner duyệt, và — sau khi DEC-001 được chấp nhận — phải có change request trong `.agent/governance/change-requests/`.

## Related Files

- `docs/04-api/openapi.yaml`
- `src/app/contracts.py`
- SRS: `docs/01-business/srs.md`

## Forbidden Actions

- Không thêm endpoint hay trường ngoài contract này khi chưa có change request.
- Không trả về PII gốc hoặc chunk thuộc phòng ban mà user không có quyền truy cập.
