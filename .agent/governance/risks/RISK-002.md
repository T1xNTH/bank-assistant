---
id: risk-002
title: CPU-only inference too slow
type: governance
domain: governance
module: risks
tags: [risk, technical]
priority: 2
---
# RISK-002: Suy luận chỉ bằng CPU quá chậm

## Record Metadata

- **Risk ID**: `RISK-002`
- **Title**: `CPU-only inference too slow`
- **Owner**: `trong-hung`
- **Status**: `identified`
- **Category**: `technical`
- **Probability**: `high`
- **Impact**: `medium`
- **Priority**: `2`
- **Created Date**: `2026-10-24`
- **Review Date**: `2026-10-28`

## Risk Statement

Nếu bge-m3, reranker và Qwen2.5 chỉ chạy trên CPU thì ingest và câu trả lời local có thể quá chậm, dẫn tới ingest chạy rất lâu và p95 của route local vượt NFR-08.

## Exposure Assessment

- **Affected Scope**: `E-003, E-004, E-010`
- **Impact Description**: trễ tiến độ so với khung 10 ngày của MVP.
- **Detection Signals**: ingest > 60 phút cho 30 PDF; câu trả lời local > 60 s
- **Assumptions**: `none`

## Related Files

- **Epics or Tasks**: `E-003, E-004, E-010`
- **Decisions**: `none`
- **Issues or Blockers**: `none`
- **Change Requests**: `none`
- **Evidence**: `none`

## Response Plan

- **Strategy**: `mitigate`
- **Mitigation Actions**: Chạy ingest nền một lần rồi snapshot Qdrant; dùng qwen2.5:3b; cache model; NFR-08 đo trên route cloud.
- **Contingency Actions**: Giảm bộ tài liệu cho CI; ghi lại latency của route local. Không dùng GPU cloud (Kaggle/Colab): A quyết định chạy toàn bộ local ngày 2026-10-27 (checklist A-6); nếu ingest vượt ngưỡng thì chạy một lần rồi `make backup` để tái dùng snapshot.
- **Trigger Threshold**: thời gian đo được trong báo cáo eval
- **Responsible Owner**: `trong-hung`

## Review Record

- **Last Reviewed Date**: `2026-10-27`
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

- Lưu thành `.agent/governance/risks/RISK-002.md`.
- Giữ nguyên mọi heading trong template này.
- Dùng link tương đối theo repo và đúng giá trị enum.
