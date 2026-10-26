---
id: test-strategy
title: Test Strategy
type: reference
domain: testing
module: tests
tags: [testing, pytest, eval]
priority: 2
---
# Chiến lược kiểm thử

| Tầng | Công cụ | Vị trí | Chạy ở đâu |
|---|---|---|---|
| Unit | pytest | `tests/unit/` | CI ở mọi PR |
| API | pytest + FastAPI TestClient, backend fake | `tests/api/` | CI ở mọi PR |
| Bảo mật | pytest (rò RBAC, quét PII, injection, HITL) | `tests/security/` | CI ở mọi PR |
| Framework | `scripts/validate-framework.py`, `tests/framework/` | | CI ở mọi PR |
| Tích hợp | pytest marker `integration` (cần compose) | `tests/integration/` | local / release QA |
| Chất lượng | RAGAS + chỉ số tự định nghĩa trên `eval/golden.jsonl` | `eval/` | job `eval` trong CI (tập con) + release QA (đầy đủ) |

Quy tắc: TDD cho phần logic; dùng fake trong `tests/fakes.py` thay vì mock phần nội bộ; output của test phải sạch; ngưỡng NFR nằm trong `eval/thresholds.json`.
