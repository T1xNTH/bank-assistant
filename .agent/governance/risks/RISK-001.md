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
- **Status**: `monitoring`
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
- **Evidence**: `.agent/reports/implementation/T-003.md; máy A theo xác nhận RISK-001 tại PR #29/529e86e; máy B chạy trực tiếp Ubuntu WSL2`

## Response Plan

- **Strategy**: `mitigate`
- **Mitigation Actions**: Cài Docker Engine + compose plugin ngay đầu N1 (cả hai máy).
- **Contingency Actions**: Chạy Qdrant/Redis bằng binary trực tiếp; tiếp tục dùng fake cho phần API.
- **Trigger Threshold**: Hết N1 mà Docker vẫn chưa chạy
- **Responsible Owner**: `teammate-b`

## Review Record

- **Last Reviewed Date**: `2026-10-27`
- **Reviewed By**: `codex`
- **Probability Change**: `decreased — Docker/Compose hoạt động trên B, A đã có xác nhận trong repo`
- **Impact Change**: `unchanged`
- **Review Evidence**: `2026-10-27: máy A đã cài Docker 29.9.2 + compose v5.6.1, make up chạy, curl /health trả ok, thêm swap 8 GB; chờ B xác nhận máy B`

Bổ sung T-003 ngày 2026-10-27: B/Ubuntu-24.04 WSL2 có Docker Engine Client/Server 29.8.2, Compose v5.6.0. Core API/Qdrant/Redis chạy thành công; API /health ok cả WSL lẫn Windows, Qdrant /readyz ok, Redis PONG; make check Linux 27 passed. Nguồn A ở dòng trước là attestation đã merge, không phải lệnh B chạy trên máy A. Chuyển monitoring, không tự đóng rủi ro trước owner review. Cần giữ phiên WSL hoạt động; distro dừng thì core dừng theo, chạy make up lại khi mở WSL.

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
