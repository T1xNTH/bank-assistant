---
id: impl-t-032-pr95-fixes
title: T-032 PR 95 review follow-up
type: report
domain: ai
module: eval
tags: [implementation, T-032, pr-95]
priority: 2
---
# T-032 PR 95 review follow-up

## Record Metadata

- **Owner**: `trong-hung`
- **Executor**: `claude`
- **Status**: `complete`
- **Date**: `2026-11-03`
- **Scope**: B review COMMENTED tại `ba18035`: đề nghị đưa bộ held-out vào repo (khiếu nại kèm đề nghị xử lý, câu hỏi bảo mật/khẩn cấp) và chạy lại eval/classify.py qua LiteLLM (máy B không có LITELLM_MASTER_KEY)
- **Commit**: xem `.agent/intelligence/git-nexus/task-commit-map.md`

## Changes

- `eval/classify_heldout.jsonl`: 18 câu không dùng khi viết prompt. 12 câu held-out của lần làm đầu (trước chỉ ở scratchpad) cộng 6 câu mới theo đề nghị của B: 3 khiếu nại kèm đề nghị xử lý, 3 câu hỏi bảo mật/khẩn cấp (`question`, `needs_human: true`). Nhãn đặt trước khi chạy model.
- `eval/results/classify.jsonl`, `eval/results/classify_heldout.jsonl`: kết quả lần chạy lại.
- `tests/unit/test_classify.py`: test bộ held-out hợp lệ, không trùng bộ 20 mẫu, có đủ các ca B nêu.
- `docs/11-integrations/n8n.md`: lệnh chạy held-out và kết quả.
- Prompt không đổi: chỉnh prompt theo held-out sẽ làm bộ này mất giá trị kiểm chứng.

## Verification

- `LLM_BACKEND=litellm python eval/classify.py` (cloud-chat, gpt-6-luna): intent 20/20 = 1.00, needs_human 20/20 = 1.00.
- `python eval/classify.py --samples eval/classify_heldout.jsonl --per-intent 0`: intent 16/18 = 0.89, needs_human 18/18 = 1.00. 2 câu sai cùng kiểu `question -> request`: "Tôi vừa bấm vào một đường link lạ và nhập mã OTP, giờ tôi phải làm gì?" và "Mất điện thoại có cài ứng dụng ngân hàng thì làm sao bảo vệ tài khoản ngay?". Cả hai vẫn `needs_human: true` nên n8n vẫn chuyển cho người. 3 khiếu nại kèm đề nghị xử lý đều đúng `complaint`.
- `pytest tests/unit/test_classify.py`: 13 passed.
- Giới hạn: B chưa tự chạy lại được với model thật (thiếu LITELLM_MASTER_KEY); số liệu trên do tác giả đo.

## Góp ý thứ hai của B tại `4af8a1a`: needs_human cho câu hỏi bảo mật chung (quyết định của A)

- B nêu: `CHAT_SYSTEM` vừa đòi `true` cho "security" vừa đòi `false` cho câu hỏi chung tra được tài liệu; câu "Hướng dẫn phòng tránh lừa đảo khi chuyển khoản?" ra `question/false`. B QA độc lập qua LiteLLM trên WSL: bộ chính 20/20 và 20/20, held-out 16/18 và 18/18, kết luận không có lỗi chặn merge.
- A chốt (2026-11-03): câu hỏi kiến thức/phòng ngừa chung không báo sự cố là `needs_human: false` (tự phục vụ qua `/ask`); sự cố thật hoặc nghi ngờ (lộ OTP/mật khẩu, đã nhận cuộc gọi/link đáng ngờ, nghi bị chiếm tài khoản, mất thẻ/điện thoại, giao dịch lạ) và việc khẩn cấp là `true`.
- `CHAT_SYSTEM` ghi rõ hai nhóm trên; `docs/11-integrations/n8n.md` cập nhật theo.
- Held-out thêm 4 câu (nhãn đặt trước khi chạy): 3 câu phòng ngừa chung (`false`, gồm câu của B) và 1 câu giao dịch lạ (`true`); tổng 22 câu. Test kiểm cặp đối chiếu.
- Chạy lại qua cloud-chat: bộ chính intent 20/20, needs_human 20/20; held-out intent 19/22 = 0.86, needs_human 22/22. 3 câu sai intent đều là câu báo sự cố kèm "giờ phải làm gì?" (`question -> complaint` 2, `question -> request` 1), vẫn `needs_human: true`. Không chỉnh nhãn sau khi chạy.
