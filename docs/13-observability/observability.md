---
id: observability-design
title: Observability Design
type: reference
domain: observability
module: tracing
tags: [observability, langfuse, cost]
priority: 2
---
# Thiết kế observability (FR-10, owner B)

Langfuse tự host (compose profile `obs`), ghim phiên bản `<5` cho Python 3.10. Input được che trước khi ghi trace (`capture_input=False` + input đã che).

## T-035: chạy local

Python SDK `langfuse==4.18.0` và server/worker `3.225.15` được ghim riêng. Stack `obs`
gồm web, ingestion worker, PostgreSQL, ClickHouse, MinIO (ghim digest) và Redis riêng.
Chỉ dashboard/OTLP web mở `127.0.0.1:3000`; các kho obs không mở port host, có volume
và healthcheck. Core API/worker không phụ thuộc profile này và không nhận mật khẩu kho obs.
Cấu hình dựa trên [Compose upstream v3.225.15](https://github.com/langfuse/langfuse/blob/v3.225.15/docker-compose.yml).

Trong `.env.local` (không commit), điền `LANGFUSE_PUBLIC_KEY=pk-lf-...`,
`LANGFUSE_SECRET_KEY=sk-lf-...`, `LANGFUSE_ADMIN_EMAIL`, `LANGFUSE_ADMIN_PASSWORD`.
Các key do người vận hành sinh ngẫu nhiên được dùng để tạo project ban đầu; nếu volume
đã có project, dùng API keys của project đó. Thay các giá trị mặc định local của
`LANGFUSE_DB_PASSWORD`, `LANGFUSE_AUTH_SECRET`, `LANGFUSE_SALT`,
`LANGFUSE_CLICKHOUSE_PASSWORD`, `LANGFUSE_REDIS_PASSWORD`, `LANGFUSE_S3_PASSWORD`
bằng chuỗi ngẫu nhiên; `LANGFUSE_ENCRYPTION_KEY` cần đúng 64 ký tự hex.

```bash
docker compose --env-file .env.local -f infrastructure/compose.yaml --profile obs up -d --wait --wait-timeout 300 langfuse langfuse-worker
# Khởi động/recreate api và worker sau khi điền API keys.
make up
```

Mở `http://localhost:3000`, đăng nhập tài khoản vừa bootstrap, chọn project Bank Assistant.
API/worker trong Compose dùng `http://langfuse:3000`; chạy Python ngoài container thì dùng
`LANGFUSE_BASE_URL=http://127.0.0.1:3000`. Thiếu một trong hai key: tracing không import SDK,
không tạo exporter/thread và không gọi mạng. `AskResponse.trace_id` giữ `null` với answerer
mặc định khi tracing tắt. Bật tracing: trường này là trace ID OTEL 32 ký tự hex thực,
trùng trace đã export và audit; polling job giữ cùng ID. Telemetry lỗi không đổi kết quả nghiệp vụ.

## Dữ liệu và span

Không dùng decorator tự capture tham số: manual instrumentation tương đương
`capture_input=False, capture_output=False`. Chỉ question/message đã che và answer được
truyền tường minh; che lại tại sink, kể cả chuỗi JSON có escape. Không ghi user object,
API key, prompt/context tài liệu, exception message hoặc stack trace. Lỗi span chỉ ghi
`Operation failed`. Exporter chỉ nhận scope `bank-assistant`; không tự thu span thư viện khác.

| Root / span | Ý nghĩa |
|---|---|
| `/ask` | Từ sau kiểm tra/masking input đến answerer trả kết quả; metadata found/route |
| `/chat` | Structured chat và kiểm tra schema; metadata intent/needs_human |
| `retrieve` | Retrieval của RAG, kể cả embed và rerank; metadata số hit/mode |
| `rerank` | Cross-encoder trong nhánh hybrid_rerank, con của retrieve |
| `llm` | Lệnh gọi model; không chứa prompt/output tự capture |
| `/ask/jobs` | Từ thời điểm RQ enqueue đến hoàn tất callable worker |
| `queue_wait` | Timestamp RQ enqueued_at đến lúc worker bắt đầu xử lý; không phải sleep giả |
| `processing` | Thực thi worker gồm chờ rate-limit, backoff và các lần gọi answerer |

`queue_wait` và `processing` là hai span cùng cha, không chồng thời gian. Job cũ không có
enqueued_at không tạo span wait. Root worker được backdate về enqueue để total latency gồm wait.
Timestamp RQ dùng UTC; các máy chạy API/worker cần đồng bộ đồng hồ. HTTP root không gồm
xác thực, masking ban đầu, serialize hoặc audit sau handler; dùng log HTTP cho end-to-end latency.
Flushing ở shutdown API và cuối mỗi job vì RQ work horse có thể thoát ngay sau job.
Nếu đặt key nhưng không bật profile `obs`, hoặc Langfuse không truy cập được, flush cuối
job có thể cộng khoảng 1–2 giây vào thời gian hoàn tất RQ (SDK timeout 2s và overhead),
kèm log export lỗi. Khoảng này nằm sau span root/processing nên không hiện trong p95
của các span đó; theo dõi thời gian hoàn tất job để thấy toàn bộ overhead. Tắt tracing
bằng cách bỏ key khi không chạy Langfuse. Mỗi work horse RQ mới cũng phải khởi tạo SDK
lại; lock chỉ bảo đảm một lần khởi tạo cho các request đồng thời trong cùng process.

## Kiểm chứng

```bash
pytest tests/unit/test_tracing.py
pytest tests/integration/test_gateway_config.py -m integration
# Export các LANGFUSE_* từ .env.local vào shell; không in key ra log.
TRACING_LIVE_TEST=1 pytest tests/integration/test_tracing_live.py -m integration
```

Live smoke dùng 20 request `/ask`, một `/chat`, hai worker call, Qdrant in-memory,
embedding/reranker/model có kịch bản và fakeredis. Nó kiểm tra ingestion SDK thật tới
stack local, ID trả về tồn tại, PII tổng hợp bị che và cây span đúng. Đây là bằng chứng
observability trên dữ liệu tổng hợp, không chứng nhận latency/model/corpus production.
Trace list đọc lại có thể trễ sau batch ingestion; smoke cho phép tối đa 90 giây.

Trong dashboard, chọn khoảng thời gian chứa smoke; xem latency percentile p95 và lọc
trace name `/ask` hoặc `/ask/jobs`. Mở một trace job: timeline có queue_wait và processing,
với retrieve → rerank và llm nằm dưới processing. Không cộng retrieve với rerank vì lồng nhau.
Kiểm tra local 2026-11-03: live smoke pass, 23 trace được ingest. Ảnh dưới đây là
dashboard Langfuse thật trên dữ liệu tổng hợp, model/embedding/reranker có kịch bản.
p95 trong ảnh không phải benchmark RAG/model production.

![Trace p95 và percentile thời gian chờ/xử lý trên dashboard](assets/T-035-latency.png)

Trace job `e3728f0d7424a838abe7c5c221c93155`: queue_wait 0,50s, processing 0,04s,
total 0,56s (có overhead giữa các span); input đã được thay bằng `<PHONE_NUMBER>`.

![Trace worker có queue_wait và processing riêng, input đã che](assets/T-035-worker.png)

## Token, chi phí và feedback (T-036)

Mỗi span `llm` thành generation với model thực trả về, `usage_details` (input/output)
và `cost_details.total` khi biết giá. Root trace giữ tổng input_tokens, output_tokens,
cost_usd trong metadata cùng found/route. Audit HTTP ghi cùng tổng vào SQLite ngay cả
khi không bật Langfuse; worker ghi một dòng xử lý riêng ở `/ask/jobs`, ngoài dòng enqueue.
Các lần gọi LLM thành công trong retry của worker được cộng dồn; output JSON không hợp lệ
vẫn giữ chi phí của lần gọi đã hoàn tất. Gateway lỗi không trả usage thì không thể ước tính
token đã tiêu thụ ở provider. Request không gọi model giữ cost_usd=NULL; model lạ hoặc
gateway thiếu usage cũng giữ NULL, không thay bằng 0 hay tổng một phần.

Giá standard text USD/1 triệu token, kiểm ngày 2026-11-03:

| Model thực | Input | Output | Nguồn |
|---|---|---|---|
| gpt-6-luna | 0.10 | 0.50 | [OpenAI](https://developers.openai.com/api/docs/models/gpt-6-luna) |
| gpt-4.1-mini, gpt-4.1-mini-2025-04-14 | 0.40 | 1.60 | [OpenAI](https://developers.openai.com/api/docs/models/gpt-4.1-mini) |
| qwen2.5:3b, qwen2.5:7b | 0 | 0 | Ollama self-hosted trong infrastructure/litellm/config.yaml; không gồm hạ tầng |

`llm_cost.PRICES` là bảng được dùng để tính; prefix openai/, ollama/, ollama_chat/ được
chuẩn hóa, alias cloud-chat/local-chat và các snapshot chưa liệt kê giữ giá chưa biết.
Đây là ước tính uncached standard short-context, không phải hóa đơn: chưa áp dụng
cache discount/write, long-context premium, service tier, regional processing, thuế
hoặc chi phí hạ tầng. Khi đổi provider/model cần kiểm nguồn và cập nhật bảng/test.
SQLite tự thêm hai cột token nullable cho DB cũ, giữ nguyên các dòng lịch sử.

`POST /feedback` dùng X-API-Key như các endpoint còn lại, body theo OpenAPI đã duyệt:
`{"trace_id":"<32 ký tự hex>","score":1,"comment":"nội dung tùy chọn"}`.
Score chỉ nhận số nguyên -1 hoặc 1, comment tối đa 1000 ký tự. SDK ghi numeric score
`user-feedback`; comment đi qua masker kể cả dạng Unicode escape, lỗi masker thì
thay bằng REDACTED. Không gửi trace_id tùy ý có thể chứa PII tới SDK. Phản hồi 204 không
có body; trace lạ, thiếu key Langfuse hoặc SDK lỗi vẫn 204 (best effort, không đảm bảo
lưu score khi telemetry tắt). Body sai hợp đồng trả 400; chưa xác thực trả 401.

Kiểm chứng: `pytest tests/unit/test_llm_cost.py tests/api/test_feedback.py
tests/api/test_request_cost.py tests/unit/test_tracing.py`.
T-037 tiếp tục xử lý rate limit/audit HTTP. Không thay contract `AskResult`/`AskResponse`.

| Chỉ số | Nguồn |
|---|---|
| Latency p50/p95 theo endpoint | thời lượng trace |
| Thời gian chờ trong hàng vs thời gian xử lý | timestamp của các span trong job |
| Token và chi phí theo request / theo ngày | `llm_cost.cost_of()` (T-036) |
| Tỉ lệ từ chối | tag `found=false` |
| Feedback 👍/👎 | `POST /feedback` → score trong Langfuse (T-036) |
