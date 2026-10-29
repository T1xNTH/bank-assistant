---
id: issue-016
title: "PR30-F06: auto-rotation damages an upright province-code table"
type: governance
domain: rag
module: src/app/rag/parse_docling.py
tags: [issue, t-006, pr-30, ocr, rotation, pr30-f06]
priority: 2
---
# ISSUE-016: Auto-rotation damages an upright table

## Record Metadata

- **Issue ID**: `ISSUE-016`
- **Owner**: `trong-hung`
- **Reporter**: `codex`
- **Status**: `resolved`
- **Issue Type**: `defect`
- **Priority**: `2`
- **Created Date**: `2026-10-28`
- **Related Work**: `T-006`, `E-003`, PR #30, `CR-007`

## Description

Real-corpus run at `7c4111316151d3ff4a35ec7e0f7e34e81f2327a6`: PDF page 109 of `145.signed.pdf` (printed page 16) is an upright three-column province/code table with 33 data rows. Before repair, the selected OCR retains 30 Markdown data rows, with recognition errors and missing cells. `_repair` judges its common-word ratio as garbled and calls `_best_rotation`. A rotated candidate raises the score only from 0.0223880597 to 0.0225563910, yet replaces the page with a transposed table containing two Markdown data rows and many columns. This damages row/column associations already available before repair.

The same output occurs at baseline `43e736f`; this is not introduced by Codex's subsequent table-preservation change. PDF page 110 remains unchanged by repair and has separate recognition defects. The failure is accepting a less complete rotated result on a tiny language-score gain, not requiring perfect OCR.

## Evidence

- [Corpus report](../../reports/qa/PR-030-corpus-20261028.md).
- `output/ocr-evaluation-20261028/visual/145-signed-109.png`: rendered source, upright.
- `output/ocr-evaluation-20261028/hard-page-inspection.json`: original, image-only, selected and final pages, scores and row counts.
- `output/ocr-evaluation-20261028/records/145.signed.json`: identical baseline/current final output.
- Source: `.review-worktrees/pr-30-fix/src/app/rag/parse_docling.py`, `_repair` and `_best_rotation` at `7c41113`.

## Acceptance Criteria

- [x] Prevent a marginal language-score improvement from replacing an upright table with a structurally degraded candidate.
- [x] Add regression coverage using captured page results, and preserve legitimate rotated-page recovery.
- [x] Recheck this real PDF page and the previously rotated pages; distinguish recognition errors from selection-induced loss.

## Resolution

- **Resolution Type**: `fixed`
- **Resolution Summary**: Rotations must both improve the score and reach the existing readable threshold; real PDF109 retains 30 data rows, PDF110 is unchanged and TT17 page28 still recovers. Code: `f0eaeac92d2cce726fb6054447812f6a5384e72a`.
- **Verification Evidence**: [Implementation report](../../reports/implementation/T-006-PR30-final-fixes.md); 101 unit tests and 3 OCR integration tests pass; regression tests fail on the old parser. Corpus replay covers 443 scan selections and 7 fallbacks; all 3 rotation-branch pages were rerun with real OCR (9 conversions).
- **Resolved By**: `codex`
- **Resolved Date**: `2026-10-29`

Resolution records an implemented and tested fix, not independent PR approval.

## Follow-up Implementation

User requested the remaining fixes on 2026-10-29. Code commit `f0eaeac92d2cce726fb6054447812f6a5384e72a`; [implementation and verification](../../reports/implementation/T-006-PR30-final-fixes.md). Independent PR review remains required.
