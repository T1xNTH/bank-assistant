---
id: blocker-002
title: T-011 cloud smoke needs Gemini credential
type: governance
domain: governance
module: infrastructure
tags: [blocker, t-011, credentials]
priority: 2
---
# BLOCKER-002: T-011 cloud smoke requires Gemini credential

## Usage Purpose

Dùng template này khi một epic hoặc task không thể tiếp tục vì một dependency, phê duyệt, quyền truy cập, quyết định hoặc lỗi cụ thể chưa được giải quyết.

## Record Metadata

- **Blocker ID**: `BLOCKER-002`
- **Title**: `Cloud-chat real-provider acceptance pending`
- **Owner**: `teammate-b`
- **Reporter**: `codex-b`
- **Status**: `open`
- **Blocker Type**: `access`
- **Priority**: `2`
- **Created Date**: `2026-10-29`
- **Target Resolution Date**: `2026-10-29`

## Blocking Condition

Nêu chính xác điều kiện đang cản trở tiến độ và bằng chứng xác nhận điều đó.

## Impact

- **Blocked Epics or Tasks**: `T-011 (E-005)`
- **Blocked Deliverables**: `Real cloud-chat ping; complete implementation report and independent review handoff`
- **Schedule or Quality Impact**: `Acceptance remains incomplete; no done or approval claim`

## Related Files

- **Affected Records**: `.agent/execution/tasks/T-011.md; .agent/reports/implementation/T-011.md`
- **Issues**: `none`
- **Decisions**: `none`
- **Risks**: `none`
- **Change Requests**: `none`

## Resolution Plan

- **Required Action**: `Owner fills GEMINI_API_KEY directly in .env.local; recreate litellm with that env file and run scripts/smoke_llm.py with both aliases`
- **Responsible Owner**: `teammate-b`
- **Dependency or Approval**: `Valid Gemini API credential and provider quota`
- **Workaround**: `none; mock responses cannot satisfy real cloud acceptance`
- **Verification Method**: `Both cloud-chat and local-chat return nonempty completions through 127.0.0.1:4000; then resolve blocker and resume lifecycle`

## Completion Criteria

- [ ] Điều kiện chặn không còn cản trở các công việc bị ảnh hưởng.
- [ ] Bằng chứng giải quyết đã được liên kết.
- [ ] Trạng thái các epic và task bị ảnh hưởng đã được cập nhật.
- [ ] Việc gỡ bỏ workaround được theo dõi khi có.

## Forbidden Actions

- Không đánh dấu `resolved` chỉ dựa trên một hành động mới được đề xuất.
- Không tiếp tục công việc bị chặn bằng một workaround chưa được phép.
- Không bỏ sót liên kết tới epic hay task bị ảnh hưởng.
- Không bịa bằng chứng giải quyết.

## Output Requirements

- Lưu thành `.agent/governance/blockers/BLOCKER-002.md`.
- Giữ nguyên mọi heading trong template này.
- Dùng link tương đối theo repo và đúng giá trị enum.
