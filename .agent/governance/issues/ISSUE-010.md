---
id: issue-010
title: "ISSUE-010: Đặt superseded_by cho TT 26/2021 khi VBHN 112 có hiệu lực (2026-11-09)"
type: governance
domain: governance
module: issues
tags: [issue, data, manifest, t-005, e-003]
priority: 2
---
# ISSUE-010: Đặt `superseded_by` cho TT 26/2021 khi VBHN 112 có hiệu lực (2026-11-09)

## Usage Purpose

Theo dõi việc theo lịch phát sinh từ PR33-F01 (review của teammate-b trên PR #33) và F-06 (review vòng 2 của `claude-review-a`). Retrieval loại chunk có `superseded_by` khác rỗng mà chưa lọc theo ngày hiệu lực, nên cặp `tt26-2021` → `tt26-2021-vbhn` chỉ được đặt từ ngày VBHN 112 có hiệu lực.

## Record Metadata

- **Issue ID**: `ISSUE-010`
- **Title**: `Đặt superseded_by cho TT 26/2021 khi VBHN 112 có hiệu lực`
- **Owner**: `trong-hung`
- **Reporter**: `teammate-b`
- **Status**: `open`
- **Issue Type**: `maintenance`
- **Priority**: `2`
- **Created Date**: `2026-10-28`
- **Target Date**: `2026-11-09`

## Description

`data/manifest.csv` hiện để trống `superseded_by` cho `tt26-2021` (TT 26/2021 bản gốc). VBHN 112 (`tt26-2021-vbhn`, gồm TT 48/2026) có hiệu lực từ 2026-11-09. `scripts/check_manifest.py` báo lỗi nếu đặt cặp trước ngày đó, nhưng không nhắc khi tới ngày.

## Impact

- **Affected Scope**: `data/manifest.csv; dữ liệu đã ingest vào Qdrant (payload superseded_by)`
- **Severity**: `low`
- **User or Delivery Impact**: `sau 2026-11-09, nếu chưa đặt cặp thì retrieval có thể trả cả TT 26/2021 bản gốc (đã lỗi thời) lẫn VBHN 112`

## Reproduction Evidence

- **Preconditions**: `ngày >= 2026-11-09`
- **Steps**: `xem dòng tt26-2021 trong data/manifest.csv`
- **Observed Result**: `superseded_by rỗng`
- **Expected Result**: `superseded_by = tt26-2021-vbhn`
- **Evidence Paths**: `https://github.com/caitoithap/bank-assistant/pull/33, docs/07-development/corpus.md`

## Related Files

- **Affected Files**: `data/manifest.csv`
- **Tasks or Epics**: `E-003 (T-005, T-010)`
- **Decisions**: `.agent/governance/decisions/DEC-001.md`
- **Risks**: `none`
- **Blockers**: `none`

## Acceptance Criteria

- [ ] Từ 2026-11-09: đặt `superseded_by = tt26-2021-vbhn` cho `tt26-2021` và `python scripts/check_manifest.py` ra `0 lỗi`.
- [ ] Nếu đã ingest: cập nhật payload `superseded_by` của các point thuộc `tt26-2021` trong Qdrant (chạy lại ingest hoặc set payload).

## Resolution

- **Resolution Type**: `not-applicable`
- **Resolution Summary**: `chưa đến ngày`
- **Verification Evidence**: `none`
- **Resolved By**: `none`
- **Resolved Date**: `none`

## Completion Criteria

- [ ] Acceptance criteria đạt.
- [ ] Bằng chứng giải quyết đã được liên kết.

## Forbidden Actions

- Không đặt cặp trước 2026-11-09.

## Output Requirements

- Lưu tại `.agent/governance/issues/ISSUE-010.md`.
- Giữ nguyên mọi heading của issue template.
