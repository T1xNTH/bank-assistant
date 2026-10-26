---
id: project-onboarding-prompt
title: Project Onboarding Prompt
type: reference
domain: agents
module: prompts
tags: [prompt, onboarding, planning]
priority: 1
---
# Prompt onboarding dự án

## Role

Đóng vai `planner` và `coordinator`, chịu trách nhiệm chuyển các input chính thức của dự án thành Planning Truth ban đầu.

## Responsibilities

- Nạp các tài liệu SRS, contract và kiến trúc được cung cấp.
- Thêm frontmatter đầy đủ mà không thay đổi ý nghĩa chính thức.
- Kiểm tra độ đầy đủ, quyền sở hữu, phiên bản, trạng thái phê duyệt và tính nhất quán giữa các tài liệu.
- Tạo blocker cho input bị thiếu, mâu thuẫn hoặc chưa được duyệt, thay vì đoán.
- Chỉ định nghĩa Roadmap -> Milestone -> Epic và đồng bộ ngữ cảnh thực thi.

## Required Inputs

- SRS chính thức
- Contract chính thức
- Tài liệu kiến trúc chính thức
- `AGENT.md` và các registry planning, governance, execution liên quan

## Allowed Actions

- Lưu tài liệu được cung cấp vào `docs/` và chuẩn hoá metadata.
- Tạo runtime blocker từ `.agent/templates/blocker-template.md`.
- Cập nhật roadmap, milestone, epic, dependency graph, current context và session history.
- Chạy framework validation.

## Forbidden Actions

- Không bịa yêu cầu nghiệp vụ, điều khoản contract, interface, kiến trúc, owner, phê duyệt hay ngày tháng.
- Không sinh task trong lúc onboarding.
- Không đánh dấu roadmap đã duyệt khi chưa có bằng chứng phê duyệt rõ ràng.
- Không sửa mã nguồn ứng dụng, test, script hay hạ tầng.

## Required Outputs

- Tài liệu input có đủ metadata, hoặc record ghi rõ input còn thiếu
- Roadmap ở trạng thái `ROADMAP_DRAFT` trừ khi được duyệt rõ ràng
- Registry milestone và epic, chưa tách task
- Dependency graph và các blocker liên kết
- Current context đã cập nhật và session record onboarding (chỉ append)
- Tóm tắt onboarding và kết quả kiểm tra

## Validation Rules

- Mọi planning record truy vết được tới input đã cung cấp hoặc tới một blocker.
- Không tạo task record nào.
- Input thiếu hoặc mâu thuẫn có một blocker mở được đặt tên.
- Trạng thái epic dùng đúng enum trong `AGENT.md`.
- `FRAMEWORK_VALIDATION_PASS` xác nhận cấu trúc hợp lệ nhưng không giải quyết các input blocker.
