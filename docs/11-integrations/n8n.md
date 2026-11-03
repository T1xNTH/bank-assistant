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

## Khởi chạy và import (T-033)

Yêu cầu Docker Compose, file `.env.local` từ `.env.example` và gateway key được điền.

```bash
make n8n-up
make n8n-import
# API + Redis + worker phải đang chạy để xử lý job:
make up
```

Profile `automation` thêm n8n `2.45.7` ở <http://127.0.0.1:5678> và Mailpit
`1.33.0` ở <http://127.0.0.1:8025> (SMTP host `mailpit`, port `1025` trong mạng
Compose). Các port host chỉ bind `127.0.0.1`. Dữ liệu n8n và encryption key tự sinh
được giữ trong volume `n8n_data`; giữ volume này khi khởi động lại. Có thể kết hợp
`COMPOSE_PROFILES=automation,local-llm`. `make n8n-up` chỉ bật hai dịch vụ automation;
`make up` với profile đã chọn bật cả API/worker và các dependency.

`make n8n-import` dùng CLI chính thức và ID ổn định `bankIntakeToReply`; chạy lại cập
nhật cùng workflow. Workflow được import ở trạng thái chưa publish, không chứa secret
hay dữ liệu mẫu pin. Dừng/unpublish workflow trước khi import lại và publish lại sau
khi kiểm tra; không dùng CLI import đồng thời với việc sửa workflow trên editor.

1. Tạo tài khoản owner local ở lần mở n8n đầu tiên.
2. Tạo API key riêng bằng `python scripts/make_key.py --user-id n8n-service
   --department public --role service`. Lệnh chỉ lưu SHA-256 vào registry; lưu giá trị
   được in một lần vào credential n8n, không commit hoặc đưa vào workflow. Chọn
   `AUTH_BACKEND=apikey` cho API và worker rồi khởi động lại chúng. Registry phải nằm
   đúng đường dẫn `API_KEYS_FILE` mà API đang mount.
3. Tạo credential **Header Auth**, tên `Bank Assistant public service`: Name
   `X-API-Key`, Value là key trên. Gắn vào cả `Classify`, `Enqueue`, `Poll job`.
4. Tạo credential **SMTP**, tên `Mailpit SMTP`: Host `mailpit`, Port `1025`, SSL/TLS
   tắt, Disable STARTTLS bật, User/Password để trống. Gắn vào `Review draft` và
   `Send reply`. ID credential khi tạo bằng UI khác ID tham chiếu trong JSON nên cần
   chọn lại credential sau import.
5. `Review draft` gửi cho `approver@example.test`; đổi địa chỉ này trong node nếu cần.
   Publish workflow, sao chép **Production URL** từ `Intake form`, không dùng test URL.
   Form path là `bank-intake`.

HTTP Request dùng URL nội bộ cố định `http://api:8000`; người gửi không điều khiển
URL hoặc API key. Không đưa provider key hay gateway key vào n8n. Code node không cần
quyền truy cập environment. Mailpit chỉ giữ thư local, không chuyển thư ra Internet.

## Kịch bản kiểm tay

1. Với `RAG_BACKEND=fake`, `LLM_BACKEND=fake`, `AUTH_BACKEND=apikey`, khởi động API,
   Redis, worker và automation. Đây là kiểm thử tích hợp, không đo chất lượng model.
   Để kiểm thử tài liệu thật, chuyển backend, ingest tài liệu department `public` rồi
   chọn câu hỏi có đáp án trong tập đó.
2. Mở Production URL, nhập Email `customer@example.test`, Message `Phí thường niên thẻ?`
   và gửi form. Giới hạn Message 1–2000 ký tự; chỉ nhận một địa chỉ email.
3. Xem execution: `Classify` → `Document question` → `Enqueue` → `Poll budget` →
   `Wait for job` → `Poll job`. Poll mỗi 5 giây, tối đa 60 lần; HTTP timeout 15 giây.
   Job `failed`, status lạ, timeout hoặc đáp án `found=true` thiếu trích dẫn đều dừng,
   không gửi phản hồi. Không tự retry POST tạo job để tránh tạo job trùng.
4. Trong Mailpit, mở thư gửi tới `approver@example.test`. Kiểm tra bản nháp có câu trả
   lời và `[n] tên file — trang p`; nhấn **Duyệt gửi**. Mở thư mới gửi tới
   `customer@example.test`: nội dung và trích dẫn phải khớp bản nháp đã duyệt.
5. Gửi form khác rồi nhấn **Từ chối**: không có thư phản hồi gửi khách. Không duyệt
   trong 24 giờ cũng không gửi: node `Approved` chỉ nhận `data.approved === true`.
6. Khi dùng model thật, thử complaint/request và câu hỏi tài khoản cần người: bỏ qua
   RAG, tạo bản nháp hướng dẫn liên hệ nhân viên và vẫn cần duyệt. `other` cũng bỏ qua
   RAG. Không gửi trực tiếp nội dung `answer` do classifier tạo ra. Nếu `found=false`,
   chỉ gửi thông báo chưa tìm thấy sau khi được duyệt.

Mọi phản hồi đều qua `Send and Wait`; liên kết duyệt là quyền tiếp tục execution,
chỉ chia sẻ cho người duyệt. Workflow này dành cho môi trường local; n8n có thể giữ
Email/Message và bản nháp trong execution đang chờ hoặc thất bại. Không nhập PII thật
vào form kiểm thử. Dữ liệu execution được prune sau 24 giờ; execution thành công không
lưu nội dung. Mailpit giữ tối đa 500 thư trong bộ nhớ. Workflow xử lý lỗi/vận hành
thuộc T-034.

### Bằng chứng chạy ngày 2026-11-03

Đã chạy trên n8n `2.45.7`, Mailpit `1.33.0`, API hiện tại với `AUTH_BACKEND=apikey`,
key `n8n-service/public/service` lưu dạng hash, Redis và worker RQ thật. LLM/RAG dùng
backend fake để kiểm tra dây chuyền tích hợp. Job được enqueue, poll qua node Wait,
hoàn tất rồi dừng chờ duyệt. Sau **Duyệt gửi**, Mailpit nhận thư cho
`customer@example.test` với `100.000 VND [1]` và `[1] bieu-phi-the.pdf — trang 3`.
Form thứ hai gửi tới `declined@example.test`, chọn **Từ chối**, không có thư trả lời.
CLI import và re-import cũng chạy trên volume n8n sạch.

![Form mẫu trước khi gửi](evidence/T-033-form.png)

![Email đã duyệt có trích dẫn trong Mailpit](evidence/T-033-mailpit-reply.png)

Nguồn tham khảo: [CLI import](https://docs.n8n.io/hosting/cli-commands/),
[Send Email và Send and Wait](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.sendemail/).

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
