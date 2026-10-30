---
id: issue-019
title: Table chunks can carry the heading of the next section on the same page
type: governance
domain: rag
module: chunk
tags: [issue, cr-009, t-007, chunk, table, docling]
priority: 2
---
# ISSUE-019: Bảng có thể mang tiêu đề của đầu mục kế tiếp trên cùng trang

## Usage Purpose

Theo dõi một giới hạn của cách chia chunk CR-009 (đã merge ở #54): tiêu đề gắn vào chunk bảng có thể sai khi trên trang có đầu mục mới bắt đầu.

## Record Metadata

- **Issue ID**: `ISSUE-019`
- **Title**: `Table chunks can carry the heading of the next section on the same page`
- **Owner**: `trong-hung`
- **Reporter**: `claude-code-a`
- **Status**: `open`
- **Issue Type**: `defect`
- **Priority**: `2`
- **Created Date**: `2026-10-30`
- **Target Date**: `none`

## Description

`parse_docling.parse()` trả về mỗi trang dạng `{text, tables}`: chữ và bảng tách riêng, không có vị trí của bảng trong trang. Vì vậy `chunk_pages` gắn cho bảng tiêu đề đang có hiệu lực ở cuối phần chữ của trang (CR-009, ghi trong docstring của `chunk.py` và `docs/07-development/ingest.md`). Ngoại lệ duy nhất là tiêu đề nằm cuối trang mà sau nó không còn chữ (F-08 của review CR-009). Khi một đầu mục mới bắt đầu sau bảng trên cùng trang, bảng mang tiêu đề của đầu mục mới.

Ví dụ thật: bảng lương tối thiểu vùng của NĐ 293/2025 (`nd293-2025`, các mức 5.310.000 / 4.730.000 / 4.140.000 / 3.700.000) thuộc Điều 3 "Mức lương tối thiểu", nhưng chunk của nó mở đầu bằng `Điều 4. Áp dụng mức lương tối thiểu`, vì Điều 4 bắt đầu trên cùng trang. Bảng cuối của 3 biểu phí VietinBank (chuyen-tien, ngan-hang-dien-tu, tai-khoan) mang tiêu đề `Lưu ý:` dù nằm trước mục đó.

## Impact

- **Affected Scope**: `chunk bảng trên trang có đầu mục mới bắt đầu: 28/136 trang có bảng, 43/245 chunk bảng, 14/30 tài liệu (đếm trên cache parse 2026-10-30; số trang có thể đúng hoặc sai, chưa đối chiếu từng bảng)`
- **Severity**: `medium`
- **User or Delivery Impact**: `Nội dung bảng và số liệu không sai; chỉ dòng tiêu đề sai. Tìm kiếm vẫn khớp nội dung bảng (12/12 câu mẫu, kể cả câu lương tối thiểu), nhưng LLM có thể trích dẫn sai Điều (ví dụ "theo Điều 4" thay vì Điều 3), ảnh hưởng tới trích dẫn ở T-018 và đánh giá ở E-008`

## Reproduction Evidence

- **Preconditions**: `cache parse của T-010 (data/cache/parsed/nd293-2025.json); chunk.py của main sau #54`
- **Steps**: `chunk_pages(pages của nd293-2025) rồi tìm chunk chứa "5.310.000"`
- **Observed Result**: `dòng đầu của chunk là "Điều 4. Áp dụng mức lương tối thiểu"`
- **Expected Result**: `dòng đầu là "Điều 3. Mức lương tối thiểu" (đầu mục chứa bảng)`
- **Evidence Paths**: `.agent/reports/implementation/T-007-CR-009.md (Known Limitations), .agent/reports/review/T-007-CR-009.md (F-07, F-08)`

## Related Files

- **Affected Files**: `src/app/rag/parse_docling.py, src/app/rag/chunk.py, tests/unit/test_chunk.py`
- **Tasks or Epics**: `T-006, T-007, CR-009, E-003; ảnh hưởng T-018 (trích dẫn) và E-008 (đánh giá)`
- **Decisions**: `DEC-001`
- **Risks**: `none`
- **Blockers**: `none`

## Acceptance Criteria

- [ ] Parser giữ thứ tự chữ và bảng trong trang (docling có thứ tự các phần tử khi đọc tài liệu), ví dụ một marker vị trí của từng bảng trong `text` hoặc danh sách phần tử theo thứ tự, mà vẫn giữ hợp đồng đầu ra hoặc có CR cho thay đổi hợp đồng.
- [ ] `chunk_pages` gắn bảng với đầu mục đứng ngay trước nó; test với một trang có bảng rồi đến Điều mới.
- [ ] Trên 30 tài liệu: bảng lương của `nd293-2025` mang `Điều 3`; đếm lại số chunk bảng đổi tiêu đề và kiểm tra mẫu.
- [ ] Parse lại (thay đổi parser làm cache parse hết hạn, khoảng 1 giờ) và ingest lại `bank_docs`; recall@5 của `tests/integration/test_retrieve_recall.py` không giảm.

## Resolution

- **Resolution Type**: `none`
- **Resolution Summary**: `none`
- **Verification Evidence**: `none`
- **Resolved By**: `none`
- **Resolved Date**: `none`

## Completion Criteria

- [ ] Acceptance criteria pass or a disposition is formally accepted.
- [ ] Resolution evidence is linked.
- [ ] Task and review records reflect the result.

## Forbidden Actions

- Không đóng issue khi chưa có bằng chứng sửa hoặc quyết định chấp nhận được ghi lại.
- Không đổi hợp đồng đầu ra của `parse()` hay `chunk_pages` mà không có CR.
- Không đoán vị trí bảng bằng heuristic theo nội dung (ví dụ bỏ qua tiêu đề "Lưu ý") thay cho vị trí thật từ docling.

## Output Requirements

- Lưu tại `.agent/governance/issues/ISSUE-019.md`.
- Giữ nguyên các heading của template.
