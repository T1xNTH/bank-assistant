---
id: blocker-003
title: T-011 real OpenAI smoke needs credential
type: governance
domain: governance
module: infrastructure
tags: [blocker, t-011, openai]
priority: 2
---
# BLOCKER-003: OpenAI runtime acceptance

## Usage Purpose

Dùng template này khi một epic hoặc task không thể tiếp tục vì một dependency, phê duyệt, quyền truy cập, quyết định hoặc lỗi cụ thể chưa được giải quyết.

## Record Metadata

- **Blocker ID**: `BLOCKER-003`
- **Title**: `Real OpenAI smoke requires a configured API key`
- **Owner**: `teammate-b`
- **Reporter**: `codex-b`
- **Status**: `open`
- **Blocker Type**: `access`
- **Priority**: `2`
- **Created Date**: `2026-10-29`
- **Target Resolution Date**: `2026-10-29`

## Blocking Condition

OPENAI_API_KEY is empty in root `.env.local`. No real OpenAI request has been made. User was asked to enter a new key directly into the file; previously exposed chat credentials were not reused. The provider migration code and controlled gateway tests are complete.

## Impact

- **Blocked Epics or Tasks**: `T-011 / E-005`
- **Blocked Deliverables**: `Real OpenAI cloud-chat ping and strict structured-output smoke`
- **Schedule or Quality Impact**: `Implementation verified with synthetic provider; real cloud acceptance and independent review pending`

## Related Files

- **Affected Records**: `.agent/execution/tasks/T-011.md; .agent/reports/implementation/T-011-openai.md`
- **Issues**: `none`
- **Decisions**: `none`
- **Risks**: `none`
- **Change Requests**: `none`

## Resolution Plan

- **Required Action**: `Owner fills OPENAI_API_KEY in git-ignored root .env.local; start LiteLLM and run scripts/smoke_llm.py --models cloud-chat, then repeat with --structured`
- **Responsible Owner**: `teammate-b`
- **Dependency or Approval**: `Valid OpenAI API credential, model access and billing/quota`
- **Workaround**: `none for real acceptance; synthetic provider tests validate routing/schema/retry boundaries only`
- **Verification Method**: `Real cloud-chat ping plus strict JSON-schema reply pass through port 4000`

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

- Lưu thành `.agent/governance/blockers/BLOCKER-003.md`.
- Giữ nguyên mọi heading trong template này.
- Dùng link tương đối theo repo và đúng giá trị enum.
