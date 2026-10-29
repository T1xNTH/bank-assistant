---
id: project-srs
title: Software Requirements Specification — bank-assistant MVP
type: reference
domain: business
module: repository
tags: [srs, requirements, mvp]
priority: 1
---
# Đặc tả yêu cầu phần mềm (SRS) — bank-assistant MVP

## Trạng thái input

- **Status**: `ingested`
- **Authority**: `draft — pending approval in DEC-001`
- **Source Artifact**: `docs/00-project/product-plan.md` (product owner duyệt ngày 2026-10-24)
- **Ingested Date**: `2026-10-24`
- **Validated By**: `trong-hung` (A), `teammate-b` (B) — cần review chéo trước DEC-001

## Mục tiêu

Trợ lý nội bộ cho nhân viên ngân hàng, trả lời câu hỏi **chỉ dựa trên tài liệu nội bộ**, luôn trích file và số trang, từ chối khi tài liệu không có câu trả lời, tôn trọng phân quyền theo phòng ban, không bao giờ làm lộ dữ liệu cá nhân, và có thể thực hiện một số thao tác nhỏ (tính lãi vay, tra cứu giao dịch, tạo ticket) với một bước duyệt bởi con người. Hệ thống theo hướng API-first và tích hợp với công cụ tự động hoá workflow (n8n).

## Phạm vi

### Bao gồm (MVP)
FR-01 … FR-12 bên dưới. Phải giao đủ tất cả — không cắt phạm vi (quyết định của product owner, 2026-10-24).

### Không bao gồm (MVP)
- SSO/OIDC, secret manager (Vault), TLS termination, HA nhiều replica, cảnh báo/trực on-call, load test, penetration test, tự động hoá lưu giữ dữ liệu, A/B prompt/model. Nằm ngoài MVP theo quyết định của product owner (2026-10-24).
- Dữ liệu khách hàng thật. Chỉ dùng tài liệu công khai và dữ liệu tổng hợp (synthetic).

## Stakeholder và nhóm người dùng

| Nhóm | Mô tả | Giá trị department |
|---|---|---|
| Nhân viên | Đặt câu hỏi, dùng agent | `public`, `credit`, `hr` |
| Người duyệt | Duyệt các hành động nhạy cảm của agent (`tao_ticket`) và phản hồi từ n8n | role `approver` |
| Vận hành | Chạy hệ thống, xem trace và chi phí | thành viên team |
| Tích hợp | Workflow n8n gọi API | API key dịch vụ |

## Yêu cầu chức năng

| ID | Yêu cầu | Tiêu chí chấp nhận (tóm tắt) |
|---|---|---|
| FR-01 | Nạp PDF (docling, bảng + OCR) → chunk → bge-m3 dense + sparse → Qdrant, payload gồm `source, page, department, classification, effective_date, superseded_by` | `scripts/ingest.py` index ≥ 30 PDF công khai; mọi point có đủ các trường payload |
| FR-02 | `POST /ask`: retrieval lai (dense + sparse, RRF) + bge-reranker-v2-m3, trả lời kèm trích dẫn (file, trang), từ chối khi dưới ngưỡng, không bao giờ trích tài liệu đã bị thay thế | JSON trả lời khớp contract; câu ngoài phạm vi → câu từ chối; tài liệu bị thay thế không bao giờ được trích |
| FR-03 | Bộ đánh giá: golden set 50 câu, chỉ số RAGAS, so sánh các mode `dense`, `hybrid`, `hybrid_rerank`, có báo cáo viết | Runner trong `eval/` tạo ra `docs/12-ai/rag-eval-report.md` |
| FR-04 | LLM gateway qua LiteLLM (OpenAI + Ollama Qwen2.5 Q4); input nhạy cảm được route sang model local | Trường `route` là `local` khi phát hiện PII/tài liệu mật |
| FR-05 | Xác thực bằng API key (key được hash) → `User(user_id, department, role)`; RBAC filter khi retrieval; audit log ai hỏi gì, lúc nào | User phòng `credit` không bao giờ nhận chunk của `hr` (có test) |
| FR-06 | Che PII (Presidio + regex VN: CCCD, số tài khoản, số điện thoại) ở input, output, log, trace, payload hàng chờ | Không có PII gốc trong log/trace/hàng chờ (có test) |
| FR-07 | Agent LangGraph với các tool `tinh_lai_vay`, `tra_cuu_giao_dich` (SQLite chỉ đọc), `tao_ticket` (người duyệt qua interrupt) | `tao_ticket` không bao giờ chạy khi chưa có quyết định của người duyệt |
| FR-08 | Workflow n8n: tiếp nhận → phân loại → `/ask` → duyệt → phản hồi; workflow xử lý lỗi | JSON workflow được export vào `infrastructure/n8n/workflows/` |
| FR-09 | Hàng chờ (Redis + RQ): `POST /ask/jobs` → 202, `GET /ask/jobs/{id}`; giới hạn tốc độ worker, retry/backoff khi 429, priority, vượt độ dài hàng chờ tối đa → 503, rate limit theo key, chỉ owner được xem kết quả | Burst vượt RPM của OpenAI vẫn hoàn tất mà người dùng không thấy lỗi |
| FR-10 | Observability bằng Langfuse: trace, token, chi phí, latency p95, thời gian chờ trong hàng vs thời gian xử lý; `POST /feedback` | Dashboard hiển thị các chỉ số đã liệt kê |
| FR-11 | Bàn giao: CI (ruff, pytest, framework validation, eval gate, trivy), compose profiles, backup/restore Qdrant | Clone mới → `make up` chạy được; CI fail khi eval tụt dưới ngưỡng |
| FR-12 | UI chat demo (Streamlit, chọn role) và tài liệu (README, kiến trúc, ADR) | Kịch bản demo chạy trọn từ đầu đến cuối |

## Yêu cầu phi chức năng

| ID | Yêu cầu | Ngưỡng | Kiểm chứng bằng |
|---|---|---|---|
| NFR-01 | Faithfulness | ≥ 0.80 | RAGAS trên golden set |
| NFR-02 | Retrieval hit@5 | ≥ 0.75 | eval runner |
| NFR-03 | Từ chối đúng với câu hỏi ngoài phạm vi | ≥ 90 % | eval runner |
| NFR-04 | Câu trả lời (trong phạm vi) có ít nhất một trích dẫn | 100 % | eval runner |
| NFR-05 | PII gốc trong log, trace, hàng chờ | 0 lần | test + quét log |
| NFR-06 | Rò RBAC giữa các phòng ban | 0 trường hợp | test |
| NFR-07 | `tao_ticket` chạy có duyệt | 100 % | test |
| NFR-08 | Latency p95 của `/ask` với OpenAI | < 10 s | Langfuse |
| NFR-09 | Provider trả 429 khi burst | 0 lỗi người dùng thấy (job được xếp hàng và retry) | test hàng chờ |
| NFR-10 | Chạy tái lập được | clone mới → `make up` healthy | release QA |

## Giả định và ràng buộc

- Team 2 người, mỗi người ~8 h/ngày, 10 ngày làm việc; Claude Code là executor agent.
- Máy: chỉ CPU (không GPU), RAM 15 GB; Docker phải được cài trong ngày 1.
- OpenAI API trả phí theo token, giới hạn theo quota/tier; ngân sách 5–6 USD theo CR-008. Model local qua Ollama trên CPU (chậm, đủ để demo).
- Python 3.10+.

## Related Files

- Contract: `docs/04-api/contract.md`
- Kiến trúc: `docs/02-architecture/architecture.md`
- Roadmap: `.agent/planning/roadmap.md`
- Danh sách epic: `.agent/planning/epics.md`

## Forbidden Actions

- Không đổi FR/NFR sau khi DEC-001 được chấp nhận nếu chưa có change request đã duyệt.
- Không dùng dữ liệu khách hàng thật.

CR-008 (approved, 2026-10-29) authorizes the cloud provider change to OpenAI. Only LiteLLM receives OPENAI_API_KEY; local routing remains unchanged. Usage is paid and subject to account quota/rate limits. The owner budget is USD 5-6; verify account spending controls before the first evaluation.
