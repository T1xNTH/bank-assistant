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
- **Status**: `resolved`
- **Blocker Type**: `access`
- **Priority**: `2`
- **Created Date**: `2026-10-29`
- **Target Resolution Date**: `2026-10-29`

## Blocking Condition

Initially OPENAI_API_KEY was empty. The user subsequently explicitly supplied a credential for the OpenAI verification. It was stored only in git-ignored root `.env.local`; no value is included here. Model access to gpt-6-luna and real gateway plain/strict structured completions passed on 2026-10-29. Evidence: `.agent/reports/implementation/T-011-openai.md`, local `output/t011-openai-real-smoke.log`.

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

- [x] Điều kiện chặn không còn cản trở các công việc bị ảnh hưởng.
- [x] Bằng chứng giải quyết đã được liên kết.
- [x] Trạng thái các epic và task bị ảnh hưởng đã được cập nhật.
- [x] Việc gỡ bỏ workaround được theo dõi khi có.

## Forbidden Actions

- Không đánh dấu `resolved` chỉ dựa trên một hành động mới được đề xuất.
- Không tiếp tục công việc bị chặn bằng một workaround chưa được phép.
- Không bỏ sót liên kết tới epic hay task bị ảnh hưởng.
- Không bịa bằng chứng giải quyết.

## Output Requirements

- Lưu thành `.agent/governance/blockers/BLOCKER-003.md`.
- Giữ nguyên mọi heading trong template này.
- Dùng link tương đối theo repo và đúng giá trị enum.

## Resolution Evidence

Real cloud-chat via host port 4000: plain and strict JSON-schema smoke both passed (exit 0). Model access verified. Two calls consumed 56 input and 15 output tokens; estimated standard cost USD 0.00001310. No independent review or full evaluation is claimed.
