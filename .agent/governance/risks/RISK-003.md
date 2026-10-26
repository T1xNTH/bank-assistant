---
id: risk-003
title: Gemini free-tier rate limits
type: governance
domain: governance
module: risks
tags: [risk, external]
priority: 2
---
# RISK-003: Giới hạn tốc độ của Gemini bản free

## Record Metadata

- **Risk ID**: `RISK-003`
- **Title**: `Gemini free-tier rate limits`
- **Owner**: `teammate-b`
- **Status**: `identified`
- **Category**: `external`
- **Probability**: `high`
- **Impact**: `medium`
- **Priority**: `2`
- **Created Date**: `2026-10-24`
- **Review Date**: `2026-10-28`

## Risk Statement

Nếu Gemini trả 429 khi chạy eval hoặc demo thì các lượt chạy fail, dẫn tới thiếu số liệu eval và demo hỏng.

## Exposure Assessment

- **Affected Scope**: `E-008, E-009, E-014`
- **Impact Description**: trễ tiến độ so với khung 10 ngày của MVP.
- **Detection Signals**: lỗi 429 trong log
- **Assumptions**: `none`

## Related Files

- **Epics or Tasks**: `E-008, E-009, E-014`
- **Decisions**: `none`
- **Issues or Blockers**: `none`
- **Change Requests**: `none`
- **Evidence**: `none`

## Response Plan

- **Strategy**: `mitigate`
- **Mitigation Actions**: Dùng hàng chờ với worker token-bucket và backoff (E-009); chạy judge với độ song song thấp; cache câu trả lời eval.
- **Contingency Actions**: Chuyển sang model local cho các lời gọi không phải judge.
- **Trigger Threshold**: > 5 % lời gọi bị 429
- **Responsible Owner**: `teammate-b`

## Review Record

- **Last Reviewed Date**: `2026-10-24`
- **Reviewed By**: `trong-hung`
- **Probability Change**: `unchanged`
- **Impact Change**: `unchanged`
- **Review Evidence**: `none`

## Completion Criteria

- [ ] Rủi ro đã được loại bỏ, được owner có thẩm quyền chấp nhận, được chuyển giao, hoặc được chuyển thành issue sau khi xảy ra.
- [ ] Trạng thái cuối và bằng chứng hỗ trợ đã được ghi lại.
- [ ] Các task, blocker, issue và decision liên quan đã được cập nhật.

## Forbidden Actions

- Không đóng một rủi ro chỉ vì đã qua ngày review.
- Không chấp nhận rủi ro high hoặc critical khi chưa xác định owner có thẩm quyền.
- Không dùng điều kiện kích hoạt mơ hồ hay hành động giảm thiểu không có owner.
- Không xoá các đánh giá trước đó khi mức độ phơi nhiễm thay đổi.

## Output Requirements

- Lưu thành `.agent/governance/risks/RISK-003.md`.
- Giữ nguyên mọi heading trong template này.
- Dùng link tương đối theo repo và đúng giá trị enum.
