---
id: release-notes-v1-0-0
title: Agentic SDLC Kit v1.0.0 Release Notes
type: reference
domain: project
module: release
tags: [release-notes, v1.0.0, framework]
priority: 1
---
# Release Notes Agentic SDLC Kit v1.0.0

## Tóm tắt release

Phiên bản `v1.0.0` đóng gói Agentic SDLC Kit (nằm ngay trong repo) thành một framework dùng lại được cho việc phát triển phần mềm có quản trị và có agent hỗ trợ.

## Kiến trúc

Kit tách riêng: chính sách vận hành lâu dài, planning truth, trạng thái thực thi, runtime governance, report làm bằng chứng, template dùng lại, tài liệu dự án và intelligence suy ra. Mã nguồn ứng dụng, test, script và hạ tầng vẫn là những vùng rõ ràng thuộc về dự án.

## Governance

Issue, blocker, change request, decision và risk có thư mục runtime riêng và template đầy đủ metadata. Change request đã duyệt bảo vệ các thứ đã chốt baseline: yêu cầu, contract, kiến trúc, cam kết roadmap, chính sách và phạm vi đã duyệt.

## Planning

Planning theo thứ tự `Roadmap -> Milestone -> Epic -> Task`. Roadmap bắt đầu ở `ROADMAP_DRAFT`; task chỉ được tách từ epic `EPIC_READY` và chỉ được thực thi khi epic ở `EPIC_IN_PROGRESS`.

## Thực thi

Current context, task board và session history (chỉ append) cung cấp trạng thái đồng bộ và bằng chứng kiểm toán. Owner rõ ràng, chuyển trạng thái, blocker, acceptance criteria, review và QA kiểm soát việc hoàn thành task.

## Intelligence

Code Graph theo dõi module, dependency, API route, cách dùng database và function. Git Nexus ánh xạ commit với task và decision, đồng thời ghi lại các regression.

## Truy xuất ngữ cảnh

Truy xuất ngữ cảnh theo task, không có thứ tự đọc bắt buộc cố định. Metadata và context package giới hạn phạm vi truy xuất vào domain, module, dependency, ràng buộc governance và output mong đợi của task đang làm.

## Onboarding

Quy trình onboarding nạp các input chính thức (SRS, contract, kiến trúc), kiểm tra metadata và độ đầy đủ, tạo blocker thay vì đoán, và chỉ dựng cây ban đầu Roadmap -> Milestone -> Epic.

## Cài đặt

Installer overlay cho Bash và PowerShell chỉ copy tài sản thuộc framework vào dự án có sẵn. Đích đã tồn tại được backup với hậu tố `.backup-agentic-sdlc-kit`, còn README, license, file package, mã nguồn, test và hạ tầng của dự án được giữ nguyên.

## Kiểm tra

Chạy `python scripts/validate-framework.py`. Framework đủ điều kiện release sẽ in `FRAMEWORK_VALIDATION_PASS`.

## Tương thích

Release này chỉ cần Python 3.10 trở lên cho script kiểm tra. Tài liệu framework và mô hình record không phụ thuộc ngôn ngữ hay nền tảng.
