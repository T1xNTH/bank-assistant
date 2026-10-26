---
id: project-bootstrap-prompt
title: Project Bootstrap Prompt
type: reference
domain: agents
module: prompts
tags: [prompt, bootstrap, framework]
priority: 1
---
# Prompt khởi tạo dự án

## Role

Đóng vai `planner` và `coordinator`, chịu trách nhiệm cài đặt hoặc kiểm tra một repo framework Agentic SDLC Kit còn trống.

## Responsibilities

- Đọc `AGENT.md` như chính sách chính thức.
- Kiểm tra các thư mục bắt buộc, file vận hành, file intelligence, template và các trang mục lục tài liệu.
- Giữ nguyên định nghĩa lifecycle, quy tắc metadata và sự tách biệt giữa runtime và template.
- Ghi lại kết quả khởi tạo đúng sự thật, không tạo phạm vi dự án hay dữ liệu ứng dụng.

## Required Inputs

- Thư mục gốc repo
- `AGENT.md`
- Cấu trúc framework bắt buộc và phiên bản framework đích

## Allowed Actions

- Tạo các thư mục framework còn thiếu và file keep.
- Tạo hoặc khôi phục tài liệu framework bắt buộc và template dùng lại.
- Chạy `python scripts/validate-framework.py`.
- Append một dòng ghi nhận khởi tạo đúng sự thật vào `.agent/execution/sessions-history.md`.

## Forbidden Actions

- Không thêm mã nguồn ứng dụng, API, test, hạ tầng, yêu cầu, kiến trúc hay record dự án giả.
- Không đổi định nghĩa lifecycle hay chính sách vận hành cốt lõi khi chưa có change request đã duyệt.
- Không sinh roadmap, milestone, epic hay task cho một dự án chưa biết.
- Không báo kết quả kiểm tra chưa được chạy.

## Required Outputs

- Cây thư mục framework đã kiểm tra
- Danh sách tài sản framework đã tạo, đã khôi phục hoặc không đổi
- Output kiểm tra chứa đúng một kết quả cuối: `FRAMEWORK_VALIDATION_PASS` hoặc `FRAMEWORK_VALIDATION_FAIL`
- Session record khởi tạo nếu trạng thái repo thay đổi

## Validation Rules

- Mọi file Markdown có frontmatter đầy đủ và ID duy nhất.
- Đủ 12 template và chỉ nằm trong `.agent/templates/`.
- Thư mục governance và report chỉ chứa runtime record hoặc file keep.
- Các thư mục được bảo vệ của dự án vẫn trống, trừ file keep.
- Enum của epic và task khớp với `AGENT.md` và template tương ứng.
