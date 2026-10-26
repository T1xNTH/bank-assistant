---
id: agentic-sdlc-kit-installation
title: Installing Agentic SDLC Kit
type: reference
domain: project
module: installation
tags: [installation, overlay, upgrade]
priority: 1
---
# Cài đặt Agentic SDLC Kit

## Mục đích

Cài kit dưới dạng framework overlay mà không thay thế định danh, mã ứng dụng, test, cấu hình package hay hạ tầng của dự án đích.

## Yêu cầu trước

- Một bản clone của repo Agentic SDLC Kit
- Một thư mục dự án đích đã tồn tại
- Bash để chạy `install-kit.sh`, hoặc PowerShell 7/Windows PowerShell để chạy `install-kit.ps1`
- Python 3.10 trở lên để kiểm tra sau khi cài

## Cài từ bản clone của kit

Clone hoặc tải kit về, rồi chạy installer từ thư mục gốc của kit.

### Bash

```bash
chmod +x scripts/install-kit.sh
./scripts/install-kit.sh /absolute/path/to/target-project
```

### PowerShell

```powershell
.\scripts\install-kit.ps1 -TargetProjectPath C:\absolute\path\to\target-project
```

Thư mục đích phải tồn tại sẵn và không được là chính thư mục kit đã clone.

Nếu thật sự muốn thay thế runtime state hiện có của dự án đích, truyền rõ cờ reset runtime:

```bash
./scripts/install-kit.sh /absolute/path/to/target-project --reset-runtime
```

```powershell
.\scripts\install-kit.ps1 -TargetProjectPath C:\absolute\path\to\target-project -ResetRuntime
```

## Cài vào dự án có sẵn

Installer thực hiện một thao tác overlay sạch:

1. Kiểm tra đường dẫn nguồn và đích.
2. Backup mọi đích overlay đã tồn tại trước khi copy.
3. Chỉ copy các tài sản framework dùng lại được: `AGENT.md`, `docs/`, `.agent/templates/`, `scripts/validate-framework.py`, hướng dẫn phân phối đã đổi tên và license của kit.
4. Khởi tạo runtime state sạch cho dự án đích trong `.agent/execution/`, `.agent/planning/` và `.agent/intelligence/`.
5. Tạo file `.keep` cho các thư mục runtime report và governance, không copy bất kỳ runtime record nào từ repo kit.
6. Không đụng tới các file và thư mục của dự án nằm ngoài overlay.
7. Chạy `python scripts/validate-framework.py` nếu có lệnh Python.
8. In ra kết quả: đã copy, đã backup, bỏ qua và kết quả kiểm tra.

Validator tự nhận biết chế độ overlay qua file `AGENTIC-SDLC-KIT.md`. Ở chế độ overlay, nó chỉ kiểm tra Markdown do kit sở hữu; Markdown khác của dự án không bắt buộc phải theo frontmatter của kit.

Installer không copy runtime report, runtime governance record, trạng thái task board, current context, planning hay intelligence từ repo kit. Các file đó được khởi tạo mới cho dự án đích. Nếu dự án đích đã có runtime file trùng tên, mặc định installer giữ nguyên và ghi là skipped. Chỉ dùng `--reset-runtime` (Bash) hoặc `-ResetRuntime` (PowerShell) khi thật sự muốn thay runtime state của dự án đích.

## Cơ chế backup

Trước khi thay một đích đã tồn tại, installer tạo bản backup nằm cạnh nó với tên:

```text
<original-path>.backup-agentic-sdlc-kit
```

Nếu tên backup đó đã có, installer thêm hậu tố `.1`, `.2`, v.v. Backup là bản chụp được copy; đích vẫn dùng được trong lúc áp overlay.

Backup thư mục áp dụng cho các thư mục dùng lại được được copy như `.agent/templates/` và `docs/`. Backup file áp dụng cho `AGENT.md`, `scripts/validate-framework.py`, `AGENTIC-SDLC-KIT.md`, `LICENSE.agentic-sdlc-kit`, và runtime file chỉ khi dùng `--reset-runtime` hoặc `-ResetRuntime`.

## Các file được copy

| Nguồn trong kit | Đích trong dự án |
|---|---|
| `AGENT.md` | `AGENT.md` |
| `.agent/templates/` | `.agent/templates/` |
| `docs/` | `docs/` |
| `scripts/validate-framework.py` | `scripts/validate-framework.py` |
| `LICENSE` | `LICENSE.agentic-sdlc-kit` |
| `README.md` | `AGENTIC-SDLC-KIT.md` |

## Runtime được khởi tạo

Installer tạo các runtime file sạch cho dự án đích nếu chúng chưa tồn tại:

- `.agent/execution/current-context.md`
- `.agent/execution/sessions-history.md`
- `.agent/execution/task-board.md`
- `.agent/planning/roadmap.md`
- `.agent/planning/milestones.md`
- `.agent/planning/epics.md`
- `.agent/planning/dependency-graph.md`
- `.agent/intelligence/code-graph/modules.md`
- `.agent/intelligence/code-graph/dependencies.md`
- `.agent/intelligence/code-graph/api-routes.md`
- `.agent/intelligence/code-graph/database-usage.md`
- `.agent/intelligence/code-graph/function-map.md`
- `.agent/intelligence/git-nexus/commit-map.md`
- `.agent/intelligence/git-nexus/task-commit-map.md`
- `.agent/intelligence/git-nexus/decision-commit-map.md`
- `.agent/intelligence/git-nexus/regression-log.md`

Trong các thư mục runtime sau, installer chỉ tạo file `.keep`:

- `.agent/reports/implementation/.keep`
- `.agent/reports/review/.keep`
- `.agent/reports/qa/.keep`
- `.agent/reports/releases/.keep`
- `.agent/governance/issues/.keep`
- `.agent/governance/blockers/.keep`
- `.agent/governance/change-requests/.keep`
- `.agent/governance/decisions/.keep`
- `.agent/governance/risks/.keep`

## Các file không bao giờ được copy

- `src/`
- `tests/`
- `infrastructure/`
- `CHANGELOG.md`
- `CONTRIBUTING.md`
- `README.md` ở gốc (dưới tên `README.md`)
- `LICENSE` ở gốc (dưới tên `LICENSE`)
- Package manifest, lock file, cấu hình build và script riêng của ứng dụng
- `.agent/reports/**/*.md`
- `.agent/governance/**/*.md`
- `.agent/execution/current-context.md` của repo kit
- `.agent/execution/task-board.md` của repo kit
- `.agent/planning/*.md` của repo kit

## Kiểm tra

Nếu có Python, installer chạy:

```bash
python scripts/validate-framework.py
```

Output khi thành công:

```text
FRAMEWORK_VALIDATION_PASS
```

Nếu không có lệnh Python, quá trình cài vẫn hoàn tất với `VALIDATION_SKIPPED_PYTHON_NOT_AVAILABLE`. Hãy chạy validator thủ công sau khi cài Python 3.10 trở lên.

## Ghi chú gỡ cài đặt

Kit cố ý không có trình gỡ cài đặt tự động mang tính phá huỷ.

1. Giữ lại mọi runtime record được tạo sau khi cài.
2. So sánh các file overlay đang dùng với danh sách file đã copy mà installer in ra.
3. Với đích có backup, dời đích hiện tại sang chỗ khác rồi khôi phục bản `.backup-agentic-sdlc-kit` tương ứng.
4. Với đích không có backup, chỉ xoá những file mà installer ghi là đã copy.
5. Chỉ xoá `AGENTIC-SDLC-KIT.md` và `LICENSE.agentic-sdlc-kit` nếu dự án đích không dùng chúng.
6. Chạy lại các kiểm tra gốc của dự án sau khi khôi phục.

Không xoá đệ quy `.agent/`, `docs/` hay `scripts/` khi chưa xem xét nội dung thuộc dự án và nội dung tạo ra sau khi cài.

## Ghi chú nâng cấp

Chạy installer của bản kit mới hơn vào cùng dự án đích. Installer tạo backup mới trước khi áp overlay nâng cấp; tên backup đã có không bao giờ bị ghi đè.

Trước khi chấp nhận một bản nâng cấp:

- review các thay đổi của `AGENT.md`, template, prompt và hành vi của validator;
- giữ lại các governance record và report do dự án đích tạo ra;
- dùng change request có quản trị cho các thay đổi về chính sách vận hành hoặc lifecycle;
- chạy framework validation sau khi cài;
- chạy các kiểm tra build, test và bảo mật gốc của dự án đích.

Một bản nâng cấp không được âm thầm đóng governance record, viết lại report đã chốt, hay sửa mã nguồn và các file định danh của dự án.
