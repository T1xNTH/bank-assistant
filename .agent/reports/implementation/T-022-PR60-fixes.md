---
id: implementation-t022-pr60-fixes
title: T-022 PR60 review corrections
type: report
domain: eval
module: eval/check_golden.py
tags: [implementation, t-022, pr-60]
priority: 3
---
# T-022 PR60 review corrections

## Usage Purpose

Bổ sung cho [implementation report gốc](T-022.md) (đã chốt, không sửa) theo review của B tại `87c6966` trong [PR #60](https://github.com/caitoithap/bank-assistant/pull/60).

## Record Metadata

- **Report ID**: `T-022-PR60-fixes`
- **Title**: `T-022 PR60 review corrections`
- **Owner**: `trong-hung`
- **Executor**: `claude-a`
- **Status**: `complete`
- **Task ID**: `T-022`
- **Epic ID**: `E-008`
- **Report Date**: `2026-10-30`

## Scope

- **Implemented**: PR60-F02: `check_golden.py` báo lỗi theo dòng khi `category`, `difficulty`, `sources[].file` hoặc `sources[].page` là list/dict, thay vì ném `TypeError: unhashable type`. PR60-F01: ghi nhận quyết định phạm vi của hai owner.
- **Not Implemented**: Không đổi `eval/golden.jsonl`, schema golden hay báo cáo gốc. Không tuyên bố review được duyệt hay task done.

## Changes Made

| File hoặc sản phẩm | Tóm tắt thay đổi | Task ID |
|---|---|---|
| `eval/check_golden.py` | `_one_of()` kiểm tra kiểu chuỗi trước khi tra tập giá trị; `file` không phải chuỗi được báo lỗi; khóa trùng nguồn dùng `repr` nên không cần hash | `T-022` |
| `tests/unit/test_check_golden.py` | 5 regression test cho list/dict ở category, difficulty, file, page | `T-022` |

## Related Files

- **Task Records**: `.agent/execution/tasks/T-022.md`
- **Context Packages**: `PR #60 review comment của B (2026-10-30T08:35:57Z)`
- **Task Board**: `.agent/execution/task-board.md`
- **Current Context**: `.agent/execution/current-context.md`
- **Decisions**: `DEC-001`
- **Change Requests**: `none`
- **Risks or Blockers**: `none`
- **Review Request**: `B re-review on PR #60; independent review claude-review-a still pending`
- **Commits**: `32bfa0b`

## Command Evidence

| Lệnh | Kết quả | Bằng chứng |
|---|---|---|
| `pytest -q tests/unit/test_check_golden.py` trước khi sửa | `failed` | `5 failed, 28 passed: cả 5 test mới ném TypeError, khớp tái hiện của B` |
| `pytest -q tests/unit/test_check_golden.py` sau khi sửa | `passed` | `33 passed` |
| `4 tái hiện nguyên văn của B trên bản sao golden.jsonl` | `passed` | `mỗi trường hợp trả đúng một lỗi "dòng 1: ..." (category, difficulty, file, page), không crash` |

## Verification Evidence

| Kiểm tra | Kết quả | Bằng chứng |
|---|---|---|
| `python3 eval/check_golden.py` | `passed` | `OK eval/golden.jsonl: 0 lỗi` |
| `make check` | `passed` | `ruff pass; 512 passed, 24 deselected; FRAMEWORK_VALIDATION_PASS` |

## Deviations

- **Plan Deviations**: `PR60-F01: task ghi "A 25 + B 25". Owner A (trong-hung) cho biết ngày 2026-10-30 rằng A và B đã thống nhất để phía A soạn đủ 50 câu; B không soạn phần riêng. Bộ 50 câu giữ nguyên.`
- **Approved By**: `A (trong-hung), báo lại thỏa thuận A–B trong hội thoại ngày 2026-10-30; B xác nhận trên PR #60 nếu cần`
- **Known Limitations**: `Ngữ nghĩa từng đáp án mới được đối chiếu tự động số liệu với data/parsed (report gốc); B ghi chưa kiểm được vì máy B không có data/parsed.`

## Completion Criteria

- [x] Mọi thay đổi được báo cáo đều ánh xạ tới một task đã được phép.
- [x] Kết quả và bằng chứng của acceptance criteria đã được liên kết.
- [x] Sai lệch và giới hạn được nêu rõ.
- [x] Kiểm tra build, lint, test đã được ghi lại hoặc đánh dấu rõ not-run kèm lý do.
- [x] Phần bàn giao cho reviewer nêu rõ một Reviewer Agent độc lập.
- [x] Ánh xạ Git Nexus được cập nhật khi đã có commit.

## Forbidden Actions

- Không báo cáo việc chưa làm là đã hiện thực.
- Không bỏ sót kiểm tra bắt buộc bị fail hoặc chưa chạy.
- Không tuyên bố hoàn thành khi acceptance criteria của task chưa đạt.
- Không tuyên bố review đã duyệt hay chuyển task sang `DONE`.
- Không đổi roadmap hay acceptance criteria.
- Không dùng report này thay cho review độc lập.
- Không đưa secret hay output lệnh nhạy cảm vào.

## Output Requirements

- Lưu thành `.agent/reports/implementation/T-022-PR60-fixes.md`.
- Giữ nguyên mọi heading và cột bảng trong template này.
- Chỉ đặt trạng thái `complete` sau khi các completion criteria đều đạt.
