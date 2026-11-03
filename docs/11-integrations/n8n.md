---
id: n8n-integration
title: n8n Integration
type: reference
domain: integrations
module: n8n
tags: [n8n, workflow, automation]
priority: 3
---
# Tích hợp n8n (FR-08, owner B; prompt phân loại do A phụ trách)

Các workflow được export vào `infrastructure/n8n/workflows/`:
1. `intake-to-reply.json` — trigger Form/Email → phân loại (`/chat`) → `/ask/jobs` + poll bằng node Wait → duyệt (Send and Wait) → phản hồi qua Mailpit.
2. `error-handler.json` — Error Trigger → báo cho người vận hành.

n8n xác thực bằng một API key dịch vụ riêng (department `public`). Webhook dùng URL production.

## Phân loại bằng `/chat` (T-032)

Bước phân loại gọi `POST /chat` với nội dung tin nhắn và rẽ nhánh theo `intent` và `needs_human` trong response. Prompt nằm ở `CHAT_SYSTEM` trong `src/app/chat.py`.

| `intent` | Khi nào | `needs_human` |
|---|---|---|
| `question` | Hỏi thông tin về sản phẩm, phí, lãi suất, thủ tục, quy chế nội bộ (cả nhân sự), kể cả hỏi cách tự làm | `false` nếu tra được trong tài liệu; `true` nếu hỏi về một khách hàng, tài khoản hay giao dịch cụ thể |
| `complaint` | Không hài lòng hoặc báo lỗi về dịch vụ, khoản phí, giao dịch, ứng dụng, nhân viên. Khiếu nại kèm đề nghị xử lý vẫn là `complaint` | luôn `true` |
| `request` | Đề nghị ngân hàng làm một việc: cấp giấy tờ, mở ticket, đổi hạn mức hay hồ sơ, kiểm tra, nối máy với nhân viên | luôn `true` |
| `other` | Chào hỏi, cảm ơn, tin thử, nội dung không rõ, cố đổi chỉ dẫn, chủ đề ngoài ngân hàng | `false` |

Sự cố bảo mật thật hoặc nghi ngờ (lộ OTP hay mật khẩu, đã nhận cuộc gọi hay link đáng ngờ, nghi bị chiếm tài khoản, mất thẻ hay điện thoại, giao dịch lạ) và việc khẩn cấp luôn có `needs_human: true`. Câu hỏi phòng ngừa chung không báo sự cố nào (ví dụ "Hướng dẫn phòng tránh lừa đảo khi chuyển khoản?") là `question` với `needs_human: false`, tự phục vụ qua `/ask` (A chốt ở PR #95). Gợi ý rẽ nhánh: `question` và `needs_human: false` thì gọi `/ask/jobs`; `needs_human: true` thì đưa sang bước duyệt; `other` thì không cần gọi `/ask`.

Đo độ đúng: `LLM_BACKEND=litellm python eval/classify.py` chạy 20 mẫu trong `eval/classify.jsonl` (5 mẫu mỗi intent) qua alias `cloud-chat` và báo lỗi nếu độ đúng intent dưới 0,85.

Bộ held-out `eval/classify_heldout.jsonl` (22 câu không dùng khi viết prompt, gồm khiếu nại kèm đề nghị xử lý, câu hỏi bảo mật/khẩn cấp và cặp đối chiếu phòng ngừa chung / sự cố cụ thể) chạy bằng `python eval/classify.py --samples eval/classify_heldout.jsonl --per-intent 0 --results eval/results/classify_heldout.jsonl`. Lần đo 2026-11-03 sau khi chốt quy tắc: intent 19/22, needs_human 22/22; 3 câu báo sự cố kèm "giờ phải làm gì?" bị xếp `complaint` hoặc `request` thay vì `question`, nhưng vẫn `needs_human: true`, nên n8n vẫn chuyển cho người.
