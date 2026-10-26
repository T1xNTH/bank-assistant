---
id: risk-004
title: Agent token limits interrupt execution
type: governance
domain: governance
module: risks
tags: [risk, delivery]
priority: 2
---
# RISK-004: Giới hạn token của agent làm gián đoạn thực thi

## Record Metadata

- **Risk ID**: `RISK-004`
- **Title**: `Agent token limits interrupt execution`
- **Owner**: `trong-hung`
- **Status**: `identified`
- **Category**: `delivery`
- **Probability**: `medium`
- **Impact**: `medium`
- **Priority**: `2`
- **Created Date**: `2026-10-24`
- **Review Date**: `2026-10-28`

## Risk Statement

Nếu chạm giới hạn sử dụng Claude Code giữa chừng task thì công việc dừng lại, dẫn tới mất giờ làm và nhánh dở dang.

## Exposure Assessment

- **Affected Scope**: `all epics`
- **Impact Description**: trễ tiến độ so với khung 10 ngày của MVP.
- **Detection Signals**: cảnh báo sử dụng ở mức 80 %
- **Assumptions**: `none`

## Related Files

- **Epics or Tasks**: `all epics`
- **Decisions**: `none`
- **Issues or Blockers**: `none`
- **Change Requests**: `none`
- **Evidence**: `none`

## Response Plan

- **Strategy**: `mitigate`
- **Mitigation Actions**: Task ≤ nửa ngày; commit WIP và cập nhật implementation report trước khi chạm giới hạn; người kia có thể làm tiếp.
- **Contingency Actions**: Đổi task giữa A và B.
- **Trigger Threshold**: mức dùng > 80 % của khung giới hạn
- **Responsible Owner**: `trong-hung`

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

- Lưu thành `.agent/governance/risks/RISK-004.md`.
- Giữ nguyên mọi heading trong template này.
- Dùng link tương đối theo repo và đúng giá trị enum.
