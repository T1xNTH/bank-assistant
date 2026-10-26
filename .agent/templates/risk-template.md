---
id: risk-template
title: Risk Template
type: governance
domain: governance
module: templates
tags: [risk, template]
priority: 2
---
# Template Risk

## Usage Purpose

Dùng template này để theo dõi một sự kiện hoặc tình huống không chắc chắn có thể ảnh hưởng tới tiến độ, chất lượng, bảo mật, tuân thủ, chi phí hoặc vận hành.

## Record Metadata

- **Risk ID**: `RISK-<number>`
- **Title**: `<required>`
- **Owner**: `<required-person-or-agent-id>`
- **Status**: `identified | analyzing | mitigating | monitoring | accepted | realized | closed`
- **Category**: `technical | delivery | security | compliance | financial | operational | external`
- **Probability**: `low | medium | high`
- **Impact**: `low | medium | high | critical`
- **Priority**: `1 | 2 | 3 | 4 | 5`
- **Created Date**: `YYYY-MM-DD`
- **Review Date**: `YYYY-MM-DD`

## Risk Statement

Viết theo mẫu: `If <cause>, then <event> may occur, resulting in <measurable impact>.` (Nếu <nguyên nhân> thì <sự kiện> có thể xảy ra, dẫn tới <ảnh hưởng đo được>.)

## Exposure Assessment

- **Affected Scope**: `<modules-documents-epics-or-tasks>`
- **Impact Description**: `<specific-impact>`
- **Detection Signals**: `<observable-signals>`
- **Assumptions**: `<assumptions-or-none>`

## Related Files

- **Epics or Tasks**: `<ids-or-none>`
- **Decisions**: `<paths-or-none>`
- **Issues or Blockers**: `<paths-or-none>`
- **Change Requests**: `<paths-or-none>`
- **Evidence**: `<paths-or-none>`

## Response Plan

- **Strategy**: `avoid | mitigate | transfer | accept`
- **Mitigation Actions**: `<task-ids-or-specific-actions>`
- **Contingency Actions**: `<actions-if-realized>`
- **Trigger Threshold**: `<observable-threshold>`
- **Responsible Owner**: `<person-or-agent-id>`

## Review Record

- **Last Reviewed Date**: `YYYY-MM-DD`
- **Reviewed By**: `<person-or-agent-id>`
- **Probability Change**: `increased | unchanged | decreased`
- **Impact Change**: `increased | unchanged | decreased`
- **Review Evidence**: `<paths>`

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

- Lưu thành `.agent/governance/risks/RISK-<number>.md`.
- Giữ nguyên mọi heading trong template này.
- Dùng link tương đối theo repo và đúng giá trị enum.
