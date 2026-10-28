---
id: development-ci
title: CI runtime checks
type: reference
domain: development
module: ci
tags: [ci, docker, smoke, api, ui]
priority: 2
---
# Kiểm tra CI

Workflow `.github/workflows/ci.yml` chạy trên pull request, push vào main và khi gọi thủ công.

| Job | Kiểm tra |
|---|---|
| `quality` | Ruff, pytest mặc định (không gồm marker integration), framework validator |
| `backend-smoke` | Build Docker image API từ Dockerfile thật; chạy API, Qdrant và Redis; gọi API qua HTTP; kiểm Qdrant readiness và Redis PONG |
| `ui-syntax` | Compile các file Python trong `ui/` |
| `check` | Gate tổng hợp: chỉ pass khi cả ba job trên thành công; job fail hoặc bị skip không được tính là pass |

Giữ tên required check `check` để cấu hình branch protection hiện có tiếp tục chặn merge khi backend smoke thất bại. Tên job lint/test cũ được đổi thành `quality`.

## Backend

CI dùng `infrastructure/compose.yaml` cùng overlay `infrastructure/compose.ci.yaml`. Overlay bỏ việc đọc `.env.local`, ép các backend sang fake và dùng địa chỉ dịch vụ trong mạng Docker. Không cần API key, model hay corpus PDF. Các dịch vụ không publish cổng host; mỗi CI run có Compose project và volume riêng.

`scripts/smoke_api.py` kiểm API đang chạy thật, không dùng TestClient hay dependency override:

- `/health` trả JSON `status=ok`.
- `/ask` trả câu trả lời, citation có file/trang và giữ mode được yêu cầu.
- Câu hỏi ngoài phạm vi được từ chối, không có citation.
- Câu hỏi rỗng trả 400; route không tồn tại trả 404; cả hai có error envelope.
- Mọi phản hồi được thử đều có UUID v4 trong `X-Request-ID`.

Qdrant được gọi trực tiếp ở `/readyz`; Redis được kiểm bằng `redis-cli -e ping`. Đây là kiểm tra khởi động stack và HTTP với fake backends; chưa chứng minh retrieval/LLM thật hay API đã sử dụng Redis/Qdrant trong luồng trả lời. Khi các tính năng đó được triển khai, bổ sung integration test riêng.

Workflow in trạng thái/log dịch vụ và dọn container, network, volume của project CI kể cả khi thất bại.

Chạy lại trên Linux/WSL, từ root repo (cần Docker Compose hỗ trợ `!reset`):

```bash
export COMPOSE_FILE=infrastructure/compose.yaml:infrastructure/compose.ci.yaml
export COMPOSE_PROJECT_NAME=bank-assistant-ci-local
docker compose config --quiet
docker compose up -d --build --wait --wait-timeout 180
docker compose exec -T api python - --qdrant-url http://qdrant:6333 < scripts/smoke_api.py
docker compose exec -T redis redis-cli -e ping
docker compose logs --no-color --tail 200
docker compose down --volumes --remove-orphans
```

Lệnh `down --volumes` chỉ dành cho project CI dùng dữ liệu tạm; giữ nguyên `COMPOSE_PROJECT_NAME` của lần chạy thử. Việc reset port trong overlay theo [quy tắc merge của Docker Compose](https://docs.docker.com/reference/compose-file/merge/#reset-value).

## Giao diện

`ui/app.py` hiện chỉ là file khung cho Streamlit. Repo chưa có frontend runtime, dependency frontend hay luồng tương tác để kiểm thử. Vì vậy job được đặt tên `ui-syntax` và ghi giới hạn này vào GitHub job summary. Job này không phải frontend build, UI startup hay browser E2E.

Khi E-016 triển khai giao diện, thay phần kiểm cú pháp bằng cài dependency, chạy ứng dụng và test gửi câu hỏi từ UI đến API. CI hiện chưa bao phủ model/OCR, toàn bộ corpus PDF hoặc các tính năng còn là stub.
