---
id: runtime-guide
title: Runtime and Delivery
type: reference
domain: devops
module: infrastructure
tags: [devops, docker, ci]
priority: 2
---
# Runtime và bàn giao

## Các lệnh
| Lệnh | Tác dụng |
|---|---|
| `make setup` | tạo `.venv`, cài `requirements-dev.txt` |
| `make check` | ruff + pytest + framework validation (đây là lệnh `agent task verify` chạy) |
| `make up` / `make down` | bật/tắt các service lõi bằng compose (`COMPOSE_PROFILES` thêm `local-llm,automation,obs`) |
| `make validate` | `python3 scripts/validate-framework.py` |
| `make backup` / `make restore` | snapshot Qdrant (FR-11) |

## CI (`.github/workflows/ci.yml`)
Job `check`: ruff, pytest (backend fake), framework validation. Thêm trong E-015: job `eval` (chặn theo ngưỡng NFR), job `trivy`.

## Môi trường
MVP chỉ có compose chạy local. Secret nằm trong `.env.local` (git ignore); `.env.example` liệt kê mọi biến.
