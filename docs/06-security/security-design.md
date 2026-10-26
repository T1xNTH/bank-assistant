---
id: security-design
title: Security Design
type: reference
domain: security
module: security
tags: [security, pii, rbac, auth]
priority: 1
---
# Thiết kế bảo mật

## Các mối đe doạ trong phạm vi (tập con của OWASP LLM Top 10)
Prompt injection (LLM01), lộ thông tin nhạy cảm (LLM02), agent có quyền quá mức (LLM06), lộ system prompt (LLM07).

## Biện pháp kiểm soát
| Biện pháp | Cách hiện thực | Owner | Test |
|---|---|---|---|
| Xác thực | `X-API-Key`, hash SHA-256 trong `config/api_keys.json`; key thật chỉ nằm trong `.env.local` | B | test 401 |
| RBAC | Qdrant filter `department ∈ {user, public}` ngay trong truy vấn | A (filter) / B (User) | test rò dữ liệu chéo phòng ban |
| Che PII | Presidio regex recognizer + mẫu VN (CCCD 12 số, số tài khoản, số điện thoại VN) ở input, output, log, trace, hàng chờ | B | test quét log/trace |
| Routing nhạy cảm | Có PII hoặc chunk `confidential` → model local | A | test routing |
| Quyền quá mức của agent | `tao_ticket` nằm sau `interrupt`; chỉ role `approver` được quyết định; DB chỉ đọc khi tra cứu | A / B | test HITL |
| Prompt injection | system prompt có canary, phân tách ngữ cảnh rõ ràng, chính sách từ chối; ≥ 10 test injection | A | `tests/security/` |
| Audit | mọi request được ghi log (đã che) kèm trace id | B | test audit |
| Chuỗi cung ứng | trivy quét image trong CI | B | CI |

## Ngoài phạm vi MVP
SSO/OIDC, secret manager, TLS, pentest (xem phần loại trừ trong SRS).
