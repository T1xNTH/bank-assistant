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

## Bộ nhận diện PII (T-020)

`src/app/security/pii.py::mask_text(text)` dùng Presidio với registry riêng và
`NoOpNlpEngine` cho tiếng Việt; không tải model spaCy. Kết quả là
`(masked_text, entity_types)`, thay toàn bộ giá trị bằng `<CCCD>`,
`<ACCOUNT_NUMBER>` hoặc `<PHONE_NUMBER>`. Danh sách loại không lặp, theo thứ tự
xuất hiện trong văn bản. Gọi lại trên văn bản đã che không thay đổi kết quả.

- CCCD: đúng 12 chữ số ASCII, có thể có một dấu cách, chấm hoặc gạch ngang giữa
  các chữ số; không nằm trong một mã chữ/số dài hơn.
- Số tài khoản: ứng viên gồm 8–19 chữ số ASCII, hỗ trợ dấu phân cách như CCCD. Không có checksum chung
  để xác thực tài khoản VN; cách che thận trọng này có thể che cả số tiền hoặc mã
  định danh dài. Số tài khoản ngoài khoảng này chưa được nhận diện.
- Điện thoại: di động bắt đầu bằng `03/05/07/08/09` (10 số), cố định `02`
  (11 số); hỗ trợ `+84`, `(+84)` và `0084` thay cho số `0` đầu, dấu cách, chấm hoặc gạch
  ngang giữa các chữ số. Không xác minh thuê bao hoặc đầu số nhà mạng cụ thể.
  Khi đã đủ độ dài, khoảng trắng hoặc dấu câu kết thúc ứng viên điện thoại,
  kể cả khi phần sau là số tiền, tài khoản hoặc một số khác. Trường hợp mơ hồ
  (ví dụ số có định dạng quá dài) vẫn che ứng viên đủ độ dài để tránh lộ PII;
  dãy chữ số liền nhau sai độ dài vẫn bị loại.
  Nhãn dính liền như `SĐT0912…`, `sdt0912…` được giữ và số được che. Ranh giới trái
  chỉ chặn chữ số hoặc `+`, nên `ref0900000001` cũng bị che thừa có chủ ý.
- Nhãn tường minh `CCCD`, `STK`, `số tài khoản` hoặc bản không dấu được ưu tiên
  khi một dãy số nhóm có thể bắt đầu giống điện thoại. Các điện thoại còn lại
  chia văn bản thành những đoạn nhận diện CCCD/tài khoản riêng, tránh gộp điện thoại
  với khoản tiền hoặc tài khoản liền sau. Trong mỗi đoạn, giữ span dài nhất;
  cùng span ưu tiên CCCD rồi tài khoản. Tài khoản 12 số không nhãn có thể mang nhãn CCCD.
  Nhãn CCCD/tài khoản cần tách khỏi số bằng dấu cách/tab hoặc dấu `:`/`=`. Với dãy
  không nhãn có tiền tố là một điện thoại hoàn chỉnh, bộ che ưu tiên điện thoại
  và xét phần sau riêng: `0900 000 001 23` thành `<PHONE_NUMBER> 23`. Không thể
  phân biệt chắc chắn đây là CCCD/tài khoản nhóm hay điện thoại kèm một số khác;
  dùng nhãn tường minh để che toàn bộ dãy thuộc CCCD/tài khoản trong trường hợp này.

Test: `pytest tests/security/test_pii.py`. Việc nối bộ che vào input, output,
log và các luồng còn lại được thực hiện ở T-021; T-015 đã gọi bộ che tại audit của `/ask`.

## Ngoài phạm vi MVP
SSO/OIDC, secret manager, TLS, pentest (xem phần loại trừ trong SRS).
