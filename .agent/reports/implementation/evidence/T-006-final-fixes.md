---
id: impl-t006-final-fixes-evidence
title: T-006 corpus verification metrics
type: report
domain: rag
module: src/app/rag/parse_docling.py
tags: [implementation, evidence, t-006, pr-30]
priority: 3
---
# T-006 corpus verification metrics

## Record Metadata

- **Owner**: `trong-hung`
- **Executor**: `codex`
- **Status**: `complete`
- **Report Date**: `2026-10-29`
- **Task ID**: `T-006`

## Evidence

Three real rotation-branch pages rerun; remaining final pages reused from the complete 30-PDF measurement. Corpus page-selection and plain fallback replays use captured real OCR results, not a second model run. Full raw observations remain in the local output artifact directory.

```json
{
  "rotation_pages_rerun": 3,
  "rotation_conversions": 9,
  "changed_pages": [
    {
      "file": "145.signed.pdf",
      "page": 109
    }
  ],
  "files": 30,
  "pages": 666,
  "method": "real OCR for all 3 rotation-branch pages; other 663 final pages reused from full corpus run",
  "parser_sha256": "ca53d62769c4f513bb11725fdcde813a8953a7cded93eeae744b8737cee02abb",
  "archive": "/mnt/d/bank-assistant/output/pr30-fixed-markdown-20261028.zip",
  "archive_sha256": "bb635b6c7d25387fb91bedc5b38d1fb48226f2be569e542b5dceb54374642383",
  "code_commit": "f0eaeac92d2cce726fb6054447812f6a5384e72a",
  "selection_and_fallback_replay": {
    "scan_pages": 443,
    "selection_changes": [],
    "fallback_replays": 7,
    "fallback_changes": []
  },
  "checks": [
    {
      "file": "145.signed.pdf",
      "page": 109,
      "changed": true,
      "kept_selected": true,
      "selected": {
        "markdown_data_rows": 30,
        "tables": 1
      },
      "before": {
        "markdown_data_rows": 2,
        "tables": 1
      },
      "after": {
        "markdown_data_rows": 30,
        "tables": 1
      },
      "score_after": 0.022388059701492536
    },
    {
      "file": "145.signed.pdf",
      "page": 110,
      "changed": false,
      "kept_selected": true,
      "selected": {
        "markdown_data_rows": 30,
        "tables": 1
      },
      "before": {
        "markdown_data_rows": 30,
        "tables": 1
      },
      "after": {
        "markdown_data_rows": 30,
        "tables": 1
      },
      "score_after": 0.022727272727272728
    },
    {
      "file": "17-nhnn.pdf",
      "page": 28,
      "changed": false,
      "kept_selected": false,
      "selected": {
        "markdown_data_rows": 0,
        "tables": 0
      },
      "before": {
        "markdown_data_rows": 0,
        "tables": 0
      },
      "after": {
        "markdown_data_rows": 0,
        "tables": 0
      },
      "score_after": 0.30625
    }
  ]
}
```
