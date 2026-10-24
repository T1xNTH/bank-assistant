---
id: product-plan
title: Product Plan — bank-assistant MVP
type: reference
domain: project
module: repository
tags: [plan, mvp, roadmap]
priority: 1
---
# Plan sản phẩm `bank-assistant` theo Agentic SDLC Kit: MVP 2 tuần, team 2 người

## Context
Lịch học đã xong và nằm trong app (`~/study-app`). Plan này **độc lập**, chỉ để build sản phẩm.
- **Team:** A (bạn) làm AI/dữ liệu; B (bạn kia, giỏi hơn) làm nền tảng/hạ tầng/bảo mật. Mỗi người ~8h/ngày, dùng Claude Code.
- **Mục tiêu:** MVP đủ chức năng sau 10 ngày làm việc, không cắt bớt.
- **Quản lý theo** `toilatrung/agentic-sdlc-kit` v1.0.0, mình đã đọc README, AGENT.md, installation, prompt pack, templates và planning registries.
  - Quy hoạch: `Roadmap → Milestone → Epic → Task`.
  - Roadmap phải được duyệt trước khi chạy. Epic chỉ được tách task khi ở trạng thái `EPIC_READY`.
  - Mỗi task: Executor (Claude Code) làm → implementation report → Reviewer độc lập → QA → done.
  - Mọi thay đổi baseline (SRS, contract, architecture) phải có change request đã duyệt.


## Bước 1: Dựng repo và cài kit (overlay)
1. `git init ~/bank-assistant`, nhánh `main`, author `trong-hung`.
2. Clone kit vào scratchpad, chạy `./scripts/install-kit.sh ~/bank-assistant`.
   - Kit copy vào: `AGENT.md`, `docs/`, `.agent/templates/`, `scripts/validate-framework.py`.
   - Kit khởi tạo runtime sạch cho `.agent/{planning,execution,intelligence}` và `.keep` cho reports/governance.
3. `python3 scripts/validate-framework.py` → phải in `FRAMEWORK_VALIDATION_PASS`.
4. **Code dự án đặt đúng chỗ kit dành sẵn:**
   - `src/app/…` (FastAPI, `rag/`, `security/`, `agent/`, `queue/`, `contracts.py`)
   - `tests/` (có `fakes.py`)
   - `infrastructure/` (Dockerfile, compose, LiteLLM config, n8n workflows)
   - `eval/`, `ui/`
   - Ở root chỉ có `pyproject.toml`, `requirements*.txt`, `.env.example`, `Makefile` (`make up`, `make test`, `make validate`).

## Bước 2: Onboarding, ba input chuẩn (kit bắt buộc có trước khi lập roadmap)
Theo `project-onboarding-prompt.md`: điền nội dung thật, có frontmatter đúng chuẩn. Chưa rõ chỗ nào thì tạo blocker, không bịa.
- **`docs/01-business/srs.md`:**
  - Mục tiêu và phạm vi; người dùng là nhân viên phòng `public`, `credit`, `hr` và người duyệt.
  - FR-01…FR-12 (bảng chức năng dưới).
  - NFR có số: faithfulness ≥ 0,8; hit@5 ≥ 0,75; từ chối đúng ≥ 90%; 100% câu trả lời có nguồn; 0 PII gốc trong log/trace; 0 rò RBAC; 100% `tao_ticket` qua người duyệt; p95 `/ask` < 10s; vượt 429 thì vào hàng chờ thay vì lỗi; clone repo mới → `make up` chạy được.
- **`docs/04-api/contract.md` + `docs/04-api/openapi.yaml`:**
  - Endpoints: `/health`, `/chat`, `/ask`, `/ask/jobs`, `/ask/jobs/{id}`, `/agent`, `/agent/{thread_id}/decision`, `/feedback`.
  - Header `X-API-Key`; mã lỗi 401/403/409/429/503; quy tắc versioning.
- **`docs/02-architecture/architecture.md`:**
  - Thành phần: api, worker RQ, redis, qdrant, litellm, ollama, n8n, langfuse, ui.
  - Luồng dữ liệu, vị trí che PII, ranh giới RBAC.
  - Hợp đồng nội bộ trong `src/app/contracts.py`: `LLM.chat`, `retrieve(question, user, k) -> list[Hit]`, `answer(question, user) -> AskResult`, `mask_text`, `User`.
  - Mỗi hợp đồng có fake tương ứng để A và B làm song song.
- **Các docs domain khác của kit:**
  - `05-database` (Qdrant payload schema: `department`, `classification`, `effective_date`, `superseded_by`; SQLite)
  - `06-security`
  - `08-devops`
  - `09-testing`
  - `11-integrations` (n8n)
  - `12-ai` (model, routing, prompt)
  - `13-observability`

## Bước 3: Planning Truth (`.agent/planning/`)
**Roadmap** `R-001`, "MVP bank-assistant, 10 ngày làm việc": trạng thái `ROADMAP_DRAFT`. Chuyển sang **`ROADMAP_APPROVED` khi bạn (vai governance) duyệt**, ghi lại bằng decision record `DEC-001`.

**Milestones:**
- `M-001` = v0.1, kết thúc N5: `/ask` thật + auth + PII + hàng chờ.
- `M-002` = v1.0-mvp, kết thúc N10: đạt toàn bộ NFR.

**Epics** (mỗi epic có một owner chịu trách nhiệm; task bên trong có thể giao người kia):
| Epic | MS | Nội dung (FR) | Owner | Ngày | Phụ thuộc |
|---|---|---|---|---|---|
| E-001 | M-001 | Baseline SRS, contract, architecture, `contracts.py` + fakes | A+B (duyệt chéo), owner A | N1 sáng | — |
| E-002 | M-001 | Nền tảng: Docker, compose (api, qdrant, redis), CI (ruff, pytest, validate-framework), branch protection | B | N1 | E-001 |
| E-003 | M-001 | Ingest: docling (bảng, OCR) → chunk → bge-m3 dense + sparse → Qdrant + metadata; 30 PDF + manifest (FR-01) | A | N1–N2 | E-001 |
| E-004 | M-001 | Retrieval + `/ask`: hybrid, RRF, rerank, trích nguồn, ngưỡng từ chối (FR-02) | A | N3–N4 | E-003 |
| E-005 | M-001 | LLM gateway: LiteLLM + Ollama, `llm.chat()`, alias (FR-04a) | B | N2 | E-002 |
| E-006 | M-001 | Auth API key (hash) → User, khung RBAC, audit log (FR-05) | B | N3 | E-002 |
| E-007 | M-001 | PII: Presidio + regex VN, che input/output/log/trace/hàng chờ (FR-06) | B | N4 | E-006 |
| E-008 | M-001 | Eval: `golden.jsonl` 50 câu (A 25 + B 25), RAGAS, so 3 mode, báo cáo (FR-03) | A | N5 | E-004 |
| E-009 | M-001 | Hàng chờ RQ: `/ask/jobs`, worker ≤ N RPM, retry/backoff, priority, 503, rate limit theo key (FR-09) | B | N5 | E-006, E-007 |
| E-010 | M-002 | Routing nhạy cảm → local, RBAC filter trong retrieve, lọc `superseded_by` (FR-04b, FR-02) | A | N6 | E-004, E-005, E-006 |
| E-011 | M-002 | Agent LangGraph + 3 tool + HITL interrupt; SQLite ro, tickets, `/agent` endpoints (FR-07) | A (task SQLite/endpoints: B) | N7–N8 | E-005, E-006 |
| E-012 | M-002 | n8n: tiếp nhận → phân loại → `/ask` → duyệt → phản hồi; workflow xử lý lỗi (FR-08) | B (prompt phân loại: A) | N8 | E-004, E-009 |
| E-013 | M-002 | Langfuse: trace, token, chi phí, p95, thời gian chờ; `/feedback` (FR-10) | B | N6 | E-005 |
| E-014 | M-002 | Vòng cải tiến chất lượng: sửa 3 câu tệ nhất từ trace, chạy lại eval | A | N9 | E-008, E-013 |
| E-015 | M-002 | Release hardening: CI eval gate, trivy, compose profiles, backup Qdrant, test clone sạch (FR-11) | B | N9–N10 | E-008, E-013 |
| E-016 | M-002 | UI Streamlit (chọn role) + README, ADR 0001–0003 (FR-12) | A | N9–N10 | E-004 |

`dependency-graph.md` ghi các cạnh ở cột Phụ thuộc, không có vòng lặp.

## Bước 4: Tách task, just-in-time
- Cuối N1: chuyển các epic của M-001 sang `EPIC_READY` và tách task theo `epic-expansion-prompt.md` (task-template; mỗi task ≤ ½ ngày, có acceptance + lệnh verify).
- Cuối N5: làm tương tự cho các epic của M-002, dựa trên những gì học được ở sprint 1.
- Ước lượng ~35–45 task tổng cộng. Ghi vào `.agent/execution/task-board.md`.

## Bước 5: Thực thi mỗi task (vòng lặp của kit)
1. Coordinator chọn task, chuẩn bị context package (`context-package-template.md`).
2. **Executor** = Claude Code trên máy của owner, nhánh `feat/T-xxx-<mô-tả>`, TDD → `.agent/reports/implementation/T-xxx.md`.
3. **Reviewer độc lập**, khác phiên executor (phiên Claude Code riêng, xem DEC-004) → `.agent/reports/review/T-xxx.md`. Sau đó người kia review PR trên GitHub.
4. **QA** gộp theo epic: pytest + eval (từ E-008) → `.agent/reports/qa/E-xxx.md`.
5. Merge (squash). Cập nhật `task-board`, `current-context`, `sessions-history`, `git-nexus/task-commit-map.md`.
6. Có vấn đề thì ghi vào `.agent/governance/`:
   - blocker khi bị chặn;
   - change request khi phải đổi contract/SRS;
   - decision record cho lựa chọn kỹ thuật (chính là ADR);
   - risk record cho rủi ro (Docker chưa có, CPU chậm, Gemini 429, hết token).
7. **Release:** cuối N5 và N10, release-manager chạy `release-manager-prompt.md` → `.agent/reports/releases/RELEASE-v0.1.md`, `RELEASE-v1.0-mvp.md`, tag git.

**Nhịp team:**
- Sync 10 phút đầu ngày.
- Merge vào `main` ít nhất 1 lần/ngày.
- Smoke test cuối ngày.
- Demo + retro cuối N5 và N10.

## Bước 6: Bàn giao GitHub (cần bạn xác nhận lúc làm)
`gh repo create` (private), push, mời collaborator, bật branch protection (1 review + CI xanh).

## Verification
- `python3 scripts/validate-framework.py` → `FRAMEWORK_VALIDATION_PASS` (chạy cả trong CI).
- `pytest` + `ruff` xanh trên khung: `/health`, contracts, `/ask` với `RAG_BACKEND=fake`.
- Roadmap/milestones/epics/dependency-graph tham chiếu được lẫn nhau. Chưa có task nào trước khi epic ở `EPIC_READY`.
- File lịch học được khôi phục nguyên trạng. Không đụng `~/study-app`.

## Quyết định đã chốt (ghi thành decision records DEC-002…DEC-005 ở bước onboarding)
1. **Trạng thái task:** dùng bộ của `AGENT.md` (`pending | in-progress | blocked | review | done | cancelled`). Ghi chú trong `docs/10-agents/index.md` rằng prompt pack được ánh xạ: IMPLEMENTED/REVIEWING → `review`, APPROVED → `done` (sau QA).
2. **Lệnh `scripts/agent` (Python stdlib, làm ở N1, ~1–2h, có test):**
   - `task start|verify|report|block|done`, `review request|start|approve|request-changes`, `qa start|pass|fail`.
   - Kiểm tra điều kiện chuyển trạng thái theo `AGENT.md`: epic phải `EPIC_IN_PROGRESS`, có owner, có report…
   - Sửa đúng dòng của task trong `task-board.md`. Tạo report từ template. Append vào `sessions-history.md`.
3. **Reviewer:** một phiên Claude Code riêng, chỉ đọc diff + implementation report, rồi viết `.agent/reports/review/T-xxx.md`. Sau đó người kia duyệt PR trên GitHub. Executor không bao giờ tự review.
4. **Báo cáo gọn:**
   - Mỗi task: implementation report + review report.
   - QA report gộp theo epic: `.agent/reports/qa/E-xxx.md`, kèm kết quả pytest/eval.
   - Mỗi PR chỉ sửa dòng task của chính mình trong `task-board.md`. `sessions-history.md` chỉ append.
   - **Bạn (A) là coordinator**, cập nhật `current-context.md` mỗi ngày.
   - Bạn là governance cho roadmap. Thay đổi contract/SRS cần cả hai cùng duyệt change request.
