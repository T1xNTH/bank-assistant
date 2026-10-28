---
id: git-nexus-task-commit-map
title: Git Nexus Task Commit Map
type: intelligence
domain: governance
module: git-nexus
tags: [git-nexus, tasks, commits]
priority: 3
---
# Task Commit Map

Ánh xạ task ID tới commit hiện thực và bằng chứng report.

| Task ID | Commit | PR | Report | Ghi chú |
|---|---|---|---|---|
| `T-001` | `54c212e, b42dc6f, 6cd249d, 71193a8, ca1f2d4, b1fd81e (executor); 18d490d, 87fcf99, 6a9bfcd (review); c9a8ce6, 3915ee0, 9129079 (follow-up)` | `#29` | `.agent/reports/implementation/T-001.md, .agent/reports/qa/T-001.md` | `commit bằng chứng trên PR #29; commit tích hợp được truy vết qua mergeCommit của https://github.com/caitoithap/bank-assistant/pull/29; QA/closure nằm trong cùng PR` |
| `T-002` | `8aa3324512fdeb67cb527dbbe68aa29aed32ee9a, f4057399cab9d7759df7281c38b92d3760a7c864, 34e54e927fbbd1e31c2c0e1540a155a7d34db80c` | `#31` | `.agent/reports/implementation/T-002.md, .agent/reports/implementation/T-002-contract-assessment.md, .agent/reports/review/T-002.md, .agent/reports/review/T-002-followup.md, .agent/reports/qa/T-002.md` | `assessment, CR-005, verification và review/QA; commit follow-up/closure truy vết qua PR #31; không triển khai CR chưa duyệt` |
| `T-003` | `3c12c02, ca06a72` | `#32` | `.agent/reports/implementation/T-003.md, .agent/reports/review/T-003.md, .agent/reports/qa/T-003.md` | `WSL Docker core readiness and smoke checks; later evidence/review commits tracked by branch PR` |
| `T-004` | `839c5f1, 103f35b, f05abfb, 0ff3f2e, 6131a71` | `#34` | `.agent/reports/implementation/T-004.md, .agent/reports/review/T-004.md, .agent/reports/qa/T-004.md, .agent/reports/implementation/T-004-followup.md, .agent/reports/review/T-004-followup.md, .agent/reports/qa/T-004-followup.md` | `API errors, IDs, JSON logs; owner fixes and merge independently APPROVED/QA passed; Windows issue migrated011; task remains review pending A PR34 approval` |
| `T-005` | `47975ba, dae6765, 495157a, 3a6f17a, 7530d06, 87ab9c9, 6c3e8fe (executor)` | `#33` | `.agent/reports/implementation/T-005.md` | `squash merge 97a0af1 vào main (PR #33)` |
