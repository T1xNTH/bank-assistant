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
| `eval-changes` | Xác định PR có đổi phần ảnh hưởng câu trả lời RAG hay eval không; quyết định có chạy `eval-gate` |
| `eval-gate` | 10 câu golden, retrieval/LLM/judge thật, mode hybrid_rerank; fail dưới ngưỡng NFR-01..04. Bỏ qua với PR không đổi đường dẫn RAG/eval |
| `ui-syntax` | Compile các file Python trong `ui/` |
| `check` | Gate tổng hợp: quality, backend-smoke (gồm Trivy), ui-syntax và eval-changes phải thành công; eval-gate phải thành công hoặc được bỏ qua khi eval-changes xác nhận PR không đổi đường dẫn RAG/eval |

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

## Eval gate (T-039)

`eval/ci-questions.json` chọn 10 câu từ `eval/golden.jsonl`: 8 câu trong phạm vi (fact, table, multi-hop),
2 câu ngoài phạm vi. `scripts/select_ci_golden.py` lấy nguyên row từ golden hiện tại, kiểm số lượng,
trùng lặp, membership, tỉ lệ 8/2 và phòng ban public. Không đọc lại điểm/câu trả lời đã lưu để quyết định pass.
Đây là smoke subset public cho hosted CI, không thay đánh giá 50 câu, RBAC/confidential, local model hay NFR-08.

**Khi nào chạy.** Push lên `main` và chạy tay (`workflow_dispatch`) luôn chạy gate. Với pull request, job
`eval-changes` so file đổi với base và chỉ chạy gate khi có đường dẫn ảnh hưởng câu trả lời hoặc cách chấm:
`src/app/rag/`, `src/app/{prompts,llm,routing,contracts}.py`, `src/app/security/masking.py`, `eval/`,
`scripts/{select_ci_golden,qdrant_backup}.py`, `infrastructure/compose.yaml`, `infrastructure/litellm/`,
`requirements*.txt`, `data/manifest.csv`, `.github/workflows/`. PR chỉ đổi docs, UI, test hay record thì
gate là `skipped` và `check` chấp nhận điều đó; nếu `eval-changes` lỗi, hoặc gate cần chạy mà không
`success`, `check` đỏ. Thêm module mới có ảnh hưởng tới câu trả lời thì phải thêm vào mẫu này.

**Judge chấm trung vị.** Mỗi câu được judge chấm faithfulness `JUDGE_REPEATS` lần (mặc định 3, số lẻ),
lấy trung vị; lần chấm lỗi gateway hay `nan` bị bỏ qua. Lý do (review PR #107, F-01): bước tách mệnh đề
của RAGAS chèn chi tiết của câu hỏi vào mệnh đề của câu trả lời ("cho khách hàng tổ chức dùng eFAST"), và
kết luận về mệnh đề đó đổi giữa các lần chấm. Câu trả lời đúng một mệnh đề (Keypass 330.000 đ/thiết bị)
bị chấm 0.0 ở cả hai lượt CI, 1/1/0 khi chấm lại ba lần trên máy. Trung vị không đổi judge, prompt hay
ngưỡng, chỉ giảm nhiễu. Không chạy lại cả lượt eval để lấy điểm pass.

Job restore snapshot `qdrant-bank_docs-2026-11-05-2819` vào Qdrant riêng của run; checksum SHA-256 ghim
trong workflow và restore kiểm đúng 2819 point. Không ingest lại từ PDF. Khi đổi corpus/chunker, phải
cập nhật snapshot/checksum cùng test và số liệu tương ứng; snapshot cũ không chứng minh chunker mới đúng.

Cần Actions secret **`OPENAI_API_KEY`** có quyền gọi `gpt-6-luna`. Chỉ gateway nhận provider key;
runner dùng key gateway tạm để trả lời và judge. Không đưa `.env.local` vào CI. Thiếu secret thì job fail
với hướng dẫn cấu hình, không skip/giả kết quả. Secret không được cấp cho fork PR: maintainer cần đưa thay đổi
đã kiểm tra lên nhánh tin cậy để chạy gate; không dùng `pull_request_target` để chạy code PR với secret.

`eval/run.py --check` chạy code RAG và prompt của PR, dùng nguyên `eval/thresholds.json`. Lỗi còn lại sau
retry, citation văn bản superseded, judge thiếu coverage hoặc metric thiếu đều fail như runner đầy đủ.
Workflow không ghim `RERANK_CANDIDATES` hay `REFUSAL_THRESHOLD`: gate dùng default từ code RAG hiện tại,
và report ghi giá trị thực tế để reviewer kiểm tra khi default thay đổi.
Không tự chạy lại một lượt fail để lấy điểm pass: dao động của judge đã được xử lý bằng trung vị ở trên. JSONL từng câu,
report, subset và backup manifest được upload artifact 14 ngày; report cũng vào job summary khi gate fail.

Lệnh tương đương trên môi trường có real gateway/Qdrant và snapshot đã restore:

```bash
python scripts/select_ci_golden.py --out output/ci-eval/golden.jsonl
LLM_BACKEND=litellm python eval/run.py --mode hybrid_rerank --golden output/ci-eval/golden.jsonl \
  --check --out output/ci-eval/report.md --results output/ci-eval/results
```

Để chứng minh gate: trên nhánh PR đang draft, tạo commit thử tạm sửa prompt buộc luôn từ chối; eval phải trả exit 1
(faithfulness dưới ngưỡng, hoặc không tính được nếu không có câu trong phạm vi được trả lời). Giữ run link của lượt đỏ,
hoàn nguyên mutation rồi chạy lại code thật trên cùng PR. Không merge prompt lỗi hoặc đổi threshold để làm xanh.

## Image vulnerability gate (T-039)

Sau build, `backend-smoke` tag chính image API đó và chạy Trivy v0.76.1 (action ghim commit v0.36.0).
Quét OS và library vulnerabilities, `severity=CRITICAL`, `ignore-unfixed=true`, `exit-code=1`.
Vì vậy CRITICAL có bản sửa làm job và required check `check` đỏ; không phải mọi HIGH hoặc CRITICAL
chưa có bản sửa đều chặn theo scope này. Lỗi scanner cũng không được bỏ qua.
JSON `trivy-api.json` được upload kể cả khi scan fail; không cần quyền ghi Security Events/SARIF.

Tham chiếu: [Trivy filtering](https://trivy.dev/docs/latest/configuration/filtering/),
[Trivy action](https://github.com/aquasecurity/trivy-action/tree/ed142fd0673e97e23eac54620cfb913e5ce36c25).

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

`ui-syntax` compile mã Streamlit. Các luồng tương tác được kiểm bằng Streamlit AppTest trong
`tests/unit/test_ui.py`, thuộc job `quality`. Đây không phải browser E2E; eval-gate cũng không đo UI.
CI không chạy OCR/reingest toàn bộ PDF hoặc chứng nhận toàn bộ 50 câu golden bằng subset 10 câu.
