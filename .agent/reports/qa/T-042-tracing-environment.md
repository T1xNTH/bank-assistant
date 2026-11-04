---
id: qa-t042-tracing-environment
title: PR 97 tracing timeout root cause
type: report
domain: testing
module: tracing
tags: [qa, pr97, environment]
priority: 2
---
# T-042 tracing timeout environment investigation

Reviewed commit: b670cbf7c15ecce325c55d85bdea07c39d4a5a8d. Source and test timeout were unchanged throughout.

## Record Metadata

- **Owner**: `codex`
- **Status**: `passed`
- **Task ID**: `T-042`
- **Report Date**: `2026-11-03`
- **Scope**: Local environment diagnosis, not a full regression rerun.

## Finding

The local QA runner places dependency overlays from the Windows-mounted filesystem on Python's search path. Importing app.tracing imports security.masking, security.pii, presidio_analyzer and its optional NLP/ML dependencies. Transformers calls importlib.metadata.packages_distributions() at module import, scanning distribution metadata on the search path. Mounted dependency directories amplify that scan and other imports beyond the test's 15-second subprocess timeout.

The timeout includes cold imports, before the fork-specific behavior is tested. It is not evidence of a fork deadlock. An independent diagnostic completed the actual fork check with exit 0.

## Measurements

| Operation | Seconds |
|---|---:|
| Empty Python process | 0.042 |
| Import tracing, mounted source and mounted pr94 dependency overlay, import profiler enabled | 24.039 |
| Import tracing, mounted source without overlay, import profiler enabled | 11.299 |
| Import tracing, Linux source without overlay, import profiler enabled | 10.220 |
| Import tracing, mounted overlay appended after site-packages, import profiler enabled | 15.477 |
| Import tracing, mounted overlay, unprofiled repeat | 25.209 |
| Import tracing, identical overlay copied to Linux, unprofiled | 12.857 |
| packages_distributions scan, mounted overlay | 10.349 |
| packages_distributions scan, base Linux environment | 1.748 |

Import profile: presidio_analyzer cumulative 22.987s with mounted overlay versus 10.360s without it. transformers.utils.import_utils self-time 8.333s versus 3.029s. Values from separate measurements are not additive and depend on cache/load.

## Controlled test result

The unchanged pytest test passes when the required pr94 overlay uses Linux storage and the unused mounted pr97 UI overlay is removed from the tracing-only runner: **1 passed, 1 warning in 27.56s**. Total pytest duration includes parent imports; the test's child retains its original 15-second limit.

Moving only pr94 while retaining the unused mounted UI overlay still fails at 15 seconds. Therefore the mitigation must remove all unnecessary mounted dependency overlays from the relevant process, not just change source-code location.

## Environment repair

Copied the identical pr94 dependency files to persistent Linux cache /home/viet_anh/.cache/bank-assistant/pr97-tracing-deps. The reusable runner output/pr97-linux-fork.py uses this cache and excludes the mounted pr94/pr97 overlays. No application source, dependency version or timeout was modified. Original failing test runs remain failed in their historical evidence.

For broader QA, keep virtualenvs and additional dependency overlays on Linux storage as well; the tracing-only runner deliberately does not load Streamlit dependencies. A future test-maintenance improvement could separate the cold-start budget from the short fork-deadlock alarm, but no such change is required to explain this failure.

## Artifacts

- results.json and *.imports.log: import measurements.
- output/pr97-root-cause.py: import-profile comparison.
- output/pr97-overlay-compare.py: mounted/Linux overlay comparison.
- output/pr97-metadata-time.py: isolated metadata scan.
- output/pr97-linux-fork.py: successful test environment, now using persistent Linux cache.
- output/pr97-r2-fork-diagnostic.py: fork diagnostic with explicit import timing.

## Published Evidence

https://github.com/T1xNTH/bank-assistant/pull/97#issuecomment-6609646936
