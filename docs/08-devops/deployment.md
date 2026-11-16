---
id: deployment-guide
title: Deployment (demo qua Cloudflare Quick Tunnel)
type: reference
domain: devops
module: infrastructure
tags: [devops, deployment, cloudflare, demo]
priority: 2
---
# Triển khai demo: API trên laptop + Cloudflare Quick Tunnel

Cách triển khai cho buổi demo/bảo vệ: toàn bộ stack chạy bằng Docker Compose trên laptop; Cloudflare Quick Tunnel cấp một URL HTTPS `https://<tên>.trycloudflare.com` trỏ về API cổng 8000 để người ngoài gọi được. Không cần domain, tài khoản Cloudflare hay mở cổng router.

Giới hạn: laptop phải bật và có mạng; URL đổi mỗi lần chạy lại tunnel; Quick Tunnel không có cam kết uptime và cắt request quá 100 giây. Chạy 24/7 với URL cố định cần named tunnel hoặc VPS (ngoài phạm vi tài liệu này).

## Chuẩn bị (một lần)

- Docker Engine + Compose (xem `wsl-docker.md`), repo đã `make setup`.
- `.env.local` dùng backend thật: `AUTH_BACKEND=apikey`, `RAG_BACKEND=real`, `LLM_BACKEND=litellm`, có `LITELLM_MASTER_KEY` và `OPENAI_API_KEY`. **Không mở tunnel khi `AUTH_BACKEND=fake`.**
- Qdrant đã có dữ liệu (collection `bank_docs`), Ollama đã có `qwen2.5:3b`.
- `cloudflared` (binary chính thức, không cần sudo):

```bash
TAG=$(gh release view -R cloudflare/cloudflared --json tagName -q .tagName)
gh release download "$TAG" -R cloudflare/cloudflared -p cloudflared-linux-amd64 -D /tmp/cf --clobber
sha256sum /tmp/cf/cloudflared-linux-amd64   # so với checksum trong release notes của $TAG
install -D -m 755 /tmp/cf/cloudflared-linux-amd64 ~/.local/bin/cloudflared
cloudflared --version
```

## 1. Khởi động stack

```bash
cd ~/bank-assistant
make up PROFILE=local-llm
# tương đương:
# docker compose -f infrastructure/compose.yaml --env-file .env.local --profile local-llm up -d --build --wait
docker compose -f infrastructure/compose.yaml --env-file .env.local --profile local-llm ps
```

Sáu service `api`, `worker`, `litellm`, `ollama`, `qdrant`, `redis` phải `healthy`.

## 2. Tạo API key cho người gọi

```bash
.venv/bin/python scripts/make_key.py --user-id demo-hoidong --department credit --role staff > ~/demo-key.txt
chmod 600 ~/demo-key.txt
```

Registry (`config/api_keys.json`, không commit) được đọc lại mỗi request nên key dùng được ngay. Không dán key vào chat, slide hay commit.

## 3. Mở tunnel (giữ terminal này chạy suốt buổi demo)

```bash
cloudflared tunnel --no-autoupdate --edge-ip-version 4 --protocol http2 --url http://127.0.0.1:8000
```

- Lấy URL trong khung `Your quick Tunnel has been created!`.
- Dòng `precheck complete` phải là `hard_fail=false`.
- `--edge-ip-version 4 --protocol http2` tránh lỗi QUIC/IPv6 (`failed to dial to edge with quic`) gặp trên một số mạng wifi.
- Chỉ tunnel **cổng 8000 (API)**. Không tunnel Streamlit UI (8501): UI nạp sẵn `UI_KEY_*` kể cả key approver; demo UI bằng cách chiếu màn hình laptop (`make ui`).

## 4. Kiểm tra

Trên máy (stack):

```bash
make smoke    # /health API, /readyz Qdrant, redis ping
```

Qua Internet (terminal khác; thay URL):

```bash
U=https://<tên>.trycloudflare.com
K=$(cat ~/demo-key.txt)

# 1) API sống -> 200
curl -s -o /dev/null -w "%{http_code}\n" $U/health

# 2) Không có key -> 401
curl -s -o /dev/null -w "%{http_code}\n" -X POST $U/ask \
  -H "Content-Type: application/json" -d '{"question":"Phí thường niên thẻ?"}'

# 3) Có key, câu hỏi thường -> "route":"cloud", có citations
curl -s -X POST $U/ask -H "X-API-Key: $K" -H "Content-Type: application/json" \
  -d '{"question":"Tổ chức tín dụng được cho vay để đáp ứng những nhu cầu vốn nào?"}' | python3 -m json.tool

# 4) Có key, câu hỏi chứa PII (CCCD giả) -> "route":"local" (Ollama/Qwen trên laptop)
curl -s -X POST $U/ask -H "X-API-Key: $K" -H "Content-Type: application/json" \
  -d '{"question":"Khách hàng có CCCD 012345678901 muốn vay vốn thì cần điều kiện gì?"}' | python3 -m json.tool
```

Kết quả đo ngày 2026-11-10 (main `1462643`): (1) 200; (2) 401; (3) `cloud`, khoảng 10 giây, trích `86-vbhn-nhnn.pdf` trang 8; (4) `local`, khoảng 16,5 giây.

Swagger: `$U/docs` liệt kê endpoint; nút "Try it out" trả 401 vì OpenAPI chưa khai báo `X-API-Key` — gọi bằng curl/Postman (header `X-API-Key`).

Muốn chắc chắn người ngoài gọi được: mở `$U/health` trên điện thoại dùng 4G.

## 5. Tắt sau demo

```bash
# Ctrl+C ở terminal tunnel, rồi:
docker compose -f infrastructure/compose.yaml --env-file .env.local --profile local-llm stop
```

Thu hồi key demo: xóa mục có `user_id` `demo-hoidong` khỏi `config/api_keys.json`.

## Xử lý sự cố

| Triệu chứng | Nguyên nhân | Cách xử lý |
|---|---|---|
| `curl: (6) Could not resolve host` ngay sau khi tạo tunnel | DNS của URL mới chưa lan truyền | Chờ 10–30 giây rồi gọi lại |
| Precheck `hard_fail=true`, `Allow outbound ... port 7844` | Mạng (thường là mạng công ty) chặn cổng 7844 | Đổi mạng (wifi nhà, 4G điện thoại) |
| `ERR Failed to dial a quic connection` / `datagram manager error` | QUIC hoặc IPv6 không ổn định | Chạy với `--edge-ip-version 4 --protocol http2` |
| `worker` unhealthy, log `Error -3 connecting to redis:6379` | Container cũ từ worktree khác (cùng project `infrastructure`) nằm trên network cũ | `docker compose -f infrastructure/compose.yaml --env-file .env.local --profile local-llm up -d --force-recreate --wait worker redis` |
| HTTP 524 | Request quá 100 giây (giới hạn Quick Tunnel) | Giữ `local-chat` (3B); không dùng model local lớn hơn qua tunnel |
| `failed to sufficiently increase receive buffer size` | Bộ đệm UDP của Linux nhỏ | Chỉ là cảnh báo, bỏ qua |

## Chi phí và an toàn

- Câu hỏi đi route cloud gọi OpenAI và tính tiền vào tài khoản trong `.env.local`: đặt giới hạn chi tiêu trên OpenAI trước buổi demo; rate limit theo key là `API_KEY_RPM` (mặc định 60/phút).
- Câu hỏi được che PII trước khi gửi cloud; câu có PII hoặc chunk `confidential` đi model local.
- Qdrant, Redis, LiteLLM, Ollama chỉ bind `127.0.0.1` và không đi qua tunnel.
