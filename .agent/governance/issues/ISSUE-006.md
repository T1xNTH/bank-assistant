---
id: issue-006
title: "ISSUE-006: Judge RAGAS trên cloud nhận context tài liệu mật khi eval"
type: governance
domain: governance
module: issues
tags: [issue, t-001, review-observation, a-3]
priority: 2
---
# ISSUE-006: Judge RAGAS trên cloud nhận context tài liệu mật khi eval

## Usage Purpose

Theo dõi quan sát A-3 trong review baseline của A (`.agent/reports/review/T-001-A-baseline.md`). A đã đồng ý và chọn phương án ngày 2026-10-27.

## Record Metadata

- **Issue ID**: `ISSUE-006`
- **Title**: `Judge RAGAS trên cloud nhận context tài liệu mật khi eval`
- **Owner**: `trong-hung`
- **Reporter**: `claude-code-a`
- **Status**: `triaged`
- **Issue Type**: `gap`
- **Priority**: `3`
- **Created Date**: `2026-10-27`
- **Target Date**: `2026-11-02`

## Description

Judge RAGAS là OpenAI (cloud), nên khi eval, câu hỏi và context được gửi lên cloud. M-001 chỉ dùng tài liệu `public` (CR-001) nên chưa ảnh hưởng; từ M-002 eval trên tài liệu `internal`/`confidential` sẽ đẩy chunk mật lên cloud.

## Impact

- **Affected Scope**: `eval/, docs/12-ai/ai-design.md`
- **Severity**: `medium`
- **User or Delivery Impact**: `eval từ M-002 có thể gửi chunk internal/confidential lên OpenAI qua judge`

## Reproduction Evidence

- **Preconditions**: `main tại 0cbf93a`
- **Steps**: `đọc các tài liệu trong Affected Scope`
- **Observed Result**: `như phần Description`
- **Expected Result**: `judge cloud chỉ nhận câu hỏi/context public; câu hỏi dùng tài liệu internal/confidential chấm bằng judge local hoặc chỉ đo hit@5 và tỉ lệ từ chối`
- **Evidence Paths**: `.agent/reports/review/T-001-A-baseline.md`

## Related Files

- **Affected Files**: `eval/, docs/12-ai/ai-design.md`
- **Tasks or Epics**: `E-008 (T-023), E-014`
- **Decisions**: `none`
- **Risks**: `none`
- **Blockers**: `none`

## Acceptance Criteria

- [x] Nguyên nhân gốc hoặc hướng xử lý đã được ghi lại.
- [ ] Kết quả khắc phục được định nghĩa bằng điều kiện quan sát được.
- [ ] Cách kiểm tra regression được định nghĩa khi cần.

## Resolution

- **Resolution Type**: `not-applicable`
- **Resolution Summary**: `Hướng xử lý A đã chọn: quy tắc judge theo classification trong eval runner (T-023 cho M-001 chỉ public; mở rộng ở E-014)`
- **Verification Evidence**: `none`
- **Resolved By**: `none`
- **Resolved Date**: `none`

## Completion Criteria

- [ ] Acceptance criteria đạt hoặc đã có hướng xử lý được duyệt.
- [ ] Bằng chứng giải quyết đã được liên kết.
- [ ] Các record task, risk, blocker và regression liên quan đã được cập nhật.

## Forbidden Actions

- Không đóng issue khi chưa có bằng chứng giải quyết.
- Không sửa SRS, contract hay kiến trúc đã duyệt khi chưa có change request đã duyệt.

## Output Requirements

- Lưu tại `.agent/governance/issues/ISSUE-006.md`.
- Giữ nguyên mọi heading của issue template.

CR-008 (approved, 2026-10-29) authorizes the cloud provider change to OpenAI. Only LiteLLM receives OPENAI_API_KEY; local routing remains unchanged. Usage is paid and subject to account quota/rate limits. The owner budget is USD 5-6; verify account spending controls before the first evaluation.
