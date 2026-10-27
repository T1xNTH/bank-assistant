---
id: wsl-docker-core-stack
title: Chạy core stack bằng Docker Engine trong WSL
type: reference
domain: devops
module: infrastructure
tags: [docker, wsl, compose, t-003]
priority: 2
---
# Chạy core stack bằng Docker Engine trong WSL

## Môi trường

Máy Windows dùng Ubuntu WSL2 và Docker Engine chạy trong distro Ubuntu. Chạy các lệnh Linux dưới đây trong terminal WSL, tại thư mục gốc checkout đang sử dụng; không dùng Python/venv Windows cho `make check` Linux. Không cần Docker Desktop cho cấu hình này.

Từ PowerShell có thể vào distro bằng `wsl -d Ubuntu-24.04`, sau đó `cd /mnt/d/bank-assistant` (hoặc đường dẫn checkout riêng của task). Giữ phiên terminal WSL hoạt động trong khi dùng stack: trên máy B, khi mọi phiên WSL kết thúc, distro có thể tự dừng và Docker/container dừng theo. Một lệnh PowerShell `wsl ... -- make up` chạy xong không thay thế phiên WSL duy trì hoạt động. T-003 không thay cấu hình idle timeout toàn máy.

## Kiểm tra công cụ

```bash
docker version
docker compose version
systemctl is-active docker
command -v make curl python3
```

`docker version` phải có cả Client và Server. Nếu Docker Engine/Compose chưa có, cài theo [hướng dẫn Ubuntu của Docker](https://docs.docker.com/engine/install/ubuntu/), rồi kiểm tra daemon và quyền truy cập socket bằng user thường. Nếu daemon chưa chạy, dùng `sudo systemctl start docker`; không thay cấu hình daemon hoặc thêm TCP listener để chạy core stack.

Chuẩn bị các công cụ phát triển còn thiếu trên Ubuntu:

```bash
sudo apt-get update
sudo apt-get install --yes make curl python3-venv
```

## Khởi động và kiểm chứng

```bash
# Giữ .env.local đã có; không ghi đè secret hoặc cấu hình của người dùng.
test -e .env.local || cp .env.example .env.local
make setup
make check
make up
make smoke
docker compose -f infrastructure/compose.yaml --env-file .env.local ps
```

`.env.example` mặc định dùng backend fake cho RAG/LLM/auth. Core smoke test không cần API key thật hoặc gọi model cloud. Tính đúng đắn của auth/RAG/queue thật được kiểm chứng ở các task sau, không suy ra từ `/health`.

`make up` build API, khởi động API/Qdrant/Redis và chờ Compose báo service ready: API có healthcheck `/health`, Redis có healthcheck `PING`, Qdrant phải đang running. Timeout mặc định 120 giây, có thể đổi bằng `make up COMPOSE_WAIT_TIMEOUT=180`.

`make smoke` kiểm riêng ba service với timeout HTTP hữu hạn: API `/health` trả `{"status":"ok"}`, Qdrant `/readyz` trả HTTP thành công, Redis trả `PONG`. Qdrant không có Docker healthcheck trong image compose này; kiểm tra readiness HTTP tách biệt, không ghi nhãn Docker `healthy` cho Qdrant.

Các port core chỉ publish trên loopback: API `127.0.0.1:8000`, Qdrant `127.0.0.1:6333`, Redis `127.0.0.1:6379`. Nếu port đã có ứng dụng khác dùng, xác định ứng dụng đó trước khi khởi động; không dừng service ngoài task để giành port.

Khi WSL đang chạy, kiểm tra thêm từ PowerShell:

```powershell
curl.exe --fail --silent --show-error http://localhost:8000/health
```

## Dừng và xem log

```bash
make logs
make down
```

`make down` không xóa named volume Qdrant. Không thêm `-v` hoặc chạy prune để xử lý lỗi khởi động. Sau khi Windows/WSL restart, vào WSL và chạy lại `make up`/`make smoke`.

`.dockerignore` loại venv, file `.env*`, dữ liệu và cấu hình key khỏi build context; Dockerfile chỉ copy runtime requirements và source. Compose vẫn đọc `.env.local` tại runtime, không đưa file này vào image.

## Bằng chứng theo máy

T-003 yêu cầu cả máy A và B: log chạy trực tiếp trên máy B/WSL được ghi trong `.agent/reports/implementation/T-003.md`; bằng chứng máy A phải ghi rõ là xác nhận đã được A đưa vào RISK-001/PR #29, không coi đó là lệnh vừa chạy trên máy A trong phiên B.
