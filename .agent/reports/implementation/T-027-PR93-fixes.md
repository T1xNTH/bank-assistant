---
id: impl-t-027-pr93-fixes
title: T-027 PR 93 review follow-up
type: report
domain: ai
module: eval
tags: [implementation, T-027, pr-93]
priority: 2
---
# T-027 PR 93 review follow-up

## Record Metadata

- **Owner**: `trong-hung`
- **Executor**: `claude`
- **Status**: `complete`
- **Date**: `2026-11-02`
- **Scope**: B review CHANGES_REQUESTED tại `fa40abc` (F-01, F-02)
- **Commit**: `9876988`, `e4ba24b`

## Changes

- **F-01** `tests/integration/test_ask.py`: route mong đợi tính từ chính các chunk truy xuất (`retrieve` + `decide_route`, cùng tham số với `/ask`); câu có nguồn `293-cp.signed.pdf` phải đi `local`.
- **F-02** `eval/run.py`: contexts giữ `classification`, kết quả ghi `route`. `judge_records` tách câu cần judge local (route khác `cloud`, hoặc có context nhãn ngoài public/internal hay thiếu nhãn) và chỉ đưa chúng cho `JUDGE_LOCAL_MODEL` (mặc định `local-chat`, chỉ nhận `local-*`, không gửi `reasoning_effort`). Không có judge local thì câu đó để trống với lý do rõ ràng, không bao giờ rơi về judge cloud.
- Docs: `docs/07-development/eval.md`, `docs/12-ai/ai-design.md`, `docs/07-development/corpus.md`, `.env.example`.

## Verification

- `pytest tests/unit/test_eval_run.py`: 50 passed (12 test mới: trả lời local-chat, judge cloud không nhận context confidential, judge local nhận, không có judge local thì unscored, nhãn lạ/thiếu fail-closed, JUDGE_LOCAL_MODEL từ chối alias cloud).
- `make check`: 855 passed, 77 deselected; Ruff; `FRAMEWORK_VALIDATION_PASS`.
- Live `pytest -m integration tests/integration/test_ask.py tests/integration/test_rbac_leak.py` (Qdrant, LiteLLM, Ollama qwen2.5:3b thật): **1 failed, 42 passed**. Route của cả 10 câu đúng; câu 1 (`Mức lương tối thiểu tháng vùng I`) giờ đi `local-chat` và qwen2.5:3b trả về chỉ `[1][1]` (3/4 lần chạy), nên trượt kiểm tra nội dung `5.310.000`. Đây là chất lượng model local, chờ A quyết định (đổi tài liệu confidential, hoặc nâng model local).
## F-03 (re-review tại `23b7661`): quyết định của A

- A chốt (2026-11-02): giữ route local theo FR-04b, không nâng model local (sản phẩm demo); chuyển nhãn `confidential` bên hr từ `nd293-2025` sang `nd158-2025` (ít được hỏi khi demo). `nd293-2025` về `public`; ingest lại 2 tài liệu (cache).
- Sau khi đổi: cả 10 câu in-scope và 2 câu out-of-scope của `test_ask.py` đi `cloud` (kiểm bằng retrieve + decide_route); 3/50 câu golden (`hybrid_rerank`) đi `local` (2 câu trả góp `vtb-dkdk-tra-gop-the-tin-dung`, 1 câu BHXH `nd158-2025`).
- `test_rbac_leak.py`: câu confidential bên hr đổi sang câu mức tham chiếu BHXH (`nd158-2025`). Kiểm tra nội dung trong `test_ask.py` giữ nguyên.
- Live `pytest -m integration tests/integration/test_ask.py tests/integration/test_rbac_leak.py tests/integration/test_retrieve_recall.py`: **47 passed**; chạy lại riêng `test_ask.py`: 16 passed.
- Giới hạn còn lại: câu nào lấy trúng chunk `confidential` (hoặc có PII) vẫn do qwen2.5:3b trả lời, chất lượng thấp hơn cloud.

- RAGAS judge local chưa chạy live: máy không có eval venv (`requirements-eval.txt`); phần chia judge đã được unit test bằng judge giả.
