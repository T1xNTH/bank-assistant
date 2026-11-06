---
id: impl-t041-key-guard-verification
title: T-041 exact assignment guard verification
type: report
domain: devops
module: ci
tags: [t-041, pr110, verification]
priority: 2
---
# T-041 exact assignment guard verification

- **Owner**: `teammate-b`
- **Executor**: `codex-b`
- **Status**: `complete`
- **Report Date**: `2026-11-06`

Supplements [the PR110 review-fix report](T-041-PR110-review-fixes.md).
The final guard counts complete lines, not substrings, and replaces only the
single exact empty assignment. A commented-out line or a differently named
variable cannot satisfy it. All checks happen before generating/writing a key.

Executed the actual embedded Python from both workflow and README: **16 cases
passed** (eight inputs per snippet): valid LF, valid CRLF, missing assignment,
sample value, inline comment, duplicate assignment, commented-out assignment,
and `OTHER_LITELLM_MASTER_KEY` assignment. Every invalid input exits nonzero
without changing the file. Valid output has exactly one sk-prefixed 64-hex key;
key values were captured for assertions and not printed in tool output.

Path coverage/parity probes, actionlint v1.7.12, framework validation and
whitespace checks passed. No runtime/model/NFR threshold changes are involved.
Hosted checks are reported separately in the PR once available.
