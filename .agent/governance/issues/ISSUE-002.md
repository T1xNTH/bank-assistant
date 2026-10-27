---
id: issue-002
title: "ISSUE-002: top_k và force_local không được truyền xuống Answerer"
type: governance
domain: governance
module: issues
tags: [issue, dec-001, review-finding, F-01]
priority: 2
---
# ISSUE-002: top_k và force_local không được truyền xuống Answerer

## Usage Purpose

Theo dõi finding F-01 trong review baseline của B (`.agent/reports/review/REVIEW-DEC-001-B.md`), được A ghi nhận khi review chéo trong T-001.

## Record Metadata

- **Issue ID**: `ISSUE-002`
- **Title**: `top_k và force_local không được truyền xuống Answerer`
- **Owner**: `trong-hung`
- **Reporter**: `claude-code-a`
- **Status**: `triaged`
- **Issue Type**: `gap`
- **Priority**: `2`
- **Created Date**: `2026-10-26`
- **Target Date**: `2026-10-29`

## Description

HTTP `POST /ask` nhận `top_k` và `force_local` (`src/app/schemas.py:12-14`, `openapi.yaml`), nhưng `Answerer.answer(question, user, mode)` (`src/app/contracts.py:74`) không có tham số tương ứng và `src/app/main.py:27` chỉ truyền `question, user, mode`. Đã kiểm chứng trên code.

## Impact

- **Affected Scope**: `docs/04-api/openapi.yaml, src/app/contracts.py, src/app/main.py`
- **Severity**: `high`
- **User or Delivery Impact**: `force_local=true có thể vẫn route sang cloud; top_k bị bỏ qua`

## Reproduction Evidence

- **Preconditions**: `main tại 0cbf93a`
- **Steps**: `đọc các file trong Affected Files`
- **Observed Result**: `như phần Description`
- **Expected Result**: `top_k và force_local đi tới retrieve/routing ở cả API và worker; force_local=true không bao giờ chọn cloud (có test)`
- **Evidence Paths**: `.agent/reports/review/REVIEW-DEC-001-B.md`

## Related Files

- **Affected Files**: `docs/04-api/openapi.yaml, src/app/contracts.py, src/app/main.py`
- **Tasks or Epics**: `E-004, E-009, E-010; trước T-019`
- **Decisions**: `.agent/governance/decisions/DEC-001.md`
- **Risks**: `none`
- **Blockers**: `none`

## Acceptance Criteria

- [ ] Nguyên nhân gốc hoặc hướng xử lý đã được ghi lại.
- [ ] Kết quả khắc phục được định nghĩa bằng điều kiện quan sát được.
- [ ] Cách kiểm tra regression được định nghĩa khi cần.
- [ ] Nếu cần đổi contract, SRS hoặc roadmap thì có change request đã duyệt.

## Resolution

- **Resolution Type**: `not-applicable`
- **Resolution Summary**: `Hướng xử lý A đã chọn (2026-10-27, checklist C-1/C-2): thêm top_k, force_local vào Answerer.answer() và mode vào Retriever.retrieve(), qua CR-003 (chờ B duyệt), trước T-016/T-019.`
- **Verification Evidence**: `none`
- **Resolved By**: `none`
- **Resolved Date**: `none`

## Completion Criteria

- [ ] Acceptance criteria đạt hoặc đã có hướng xử lý được duyệt.
- [ ] Bằng chứng giải quyết đã được liên kết.
- [ ] Các record task, risk, blocker và regression liên quan đã được cập nhật.

## Forbidden Actions

- Không đóng issue khi chưa có bằng chứng giải quyết hoặc hướng xử lý được duyệt.
- Không sửa `openapi.yaml`, `contracts.py`, SRS hay roadmap khi chưa có change request đã duyệt.

## Output Requirements

- Lưu tại `.agent/governance/issues/ISSUE-002.md`.
- Giữ nguyên mọi heading của issue template.
