---
id: risk-001
title: Docker not installed on development machines
type: governance
domain: governance
module: risks
tags: [risk, delivery]
priority: 2
---
# RISK-001: Máy phát triển chưa cài Docker

## Record Metadata

- **Risk ID**: `RISK-001`
- **Title**: `Docker not installed on development machines`
- **Owner**: `teammate-b`
- **Status**: `identified`
- **Category**: `delivery`
- **Probability**: `high`
- **Impact**: `high`
- **Priority**: `2`
- **Created Date**: `2026-10-24`
- **Review Date**: `2026-10-28`

## Risk Statement

Nếu Docker chưa được cài trong N1 thì các epic dựa trên compose không thể bắt đầu, dẫn tới E-002 và mọi epic phụ thuộc bị trễ.

## Exposure Assessment

- **Affected Scope**: `E-002, E-005, E-009`
- **Impact Description**: trễ tiến độ so với khung 10 ngày của MVP.
- **Detection Signals**: `docker version` fail vào chiều N1
- **Assumptions**: `none`

## Related Files

- **Epics or Tasks**: `E-002, E-005, E-009`
- **Decisions**: `none`
- **Issues or Blockers**: `none`
- **Change Requests**: `none`
- **Evidence**: `none`

## Response Plan

- **Strategy**: `mitigate`
- **Mitigation Actions**: Cài Docker Engine + compose plugin ngay đầu N1 (cả hai máy).
- **Contingency Actions**: Chạy Qdrant/Redis bằng binary trực tiếp; tiếp tục dùng fake cho phần API.
- **Trigger Threshold**: Hết N1 mà Docker vẫn chưa chạy
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

- Lưu thành `.agent/governance/risks/RISK-001.md`.
- Giữ nguyên mọi heading trong template này.
- Dùng link tương đối theo repo và đúng giá trị enum.
