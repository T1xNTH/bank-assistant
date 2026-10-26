---
id: release-report-template
title: Release Report Template
type: report
domain: releases
module: templates
tags: [release, report, template]
priority: 2
---
# Template Release Report

## Usage Purpose

Dùng template này để cho phép, truy vết và ghi lại một lần release cùng kết quả triển khai.

## Record Metadata

- **Report ID**: `REL-<number>`
- **Release Version**: `<semantic-version-or-project-version>`
- **Title**: `<required>`
- **Owner**: `<required-person-or-agent-id>`
- **Release Manager**: `<required-person-or-agent-id>`
- **Status**: `planned | ready | approved | deploying | deployed | failed | rolled-back | cancelled | superseded`
- **Target Environment**: `<environment-name-or-id>`
- **Planned Date**: `YYYY-MM-DD`
- **Actual Date**: `YYYY-MM-DD | pending`

## Release Scope

- **Included Epics or Tasks**: `<ids>`
- **Included Commits**: `<hashes-or-range>`
- **Included Artifacts**: `<artifact-identifiers>`
- **Excluded or Deferred Items**: `<items-or-none>`

## Related Files

- **Implementation Reports**: `<paths>`
- **Review Reports**: `<paths>`
- **QA Reports**: `<paths>`
- **Change Requests**: `<paths-or-none>`
- **Decisions**: `<paths-or-none>`
- **Risks and Known Issues**: `<paths-or-none>`

## Readiness Checks

- [ ] Các implementation report bắt buộc đã hoàn thành.
- [ ] Các review bắt buộc đã được duyệt.
- [ ] Khuyến nghị QA là `go` hoặc `conditional-go` đã được cho phép.
- [ ] Quy trình triển khai và rollback đã được kiểm chứng.
- [ ] Các phê duyệt bắt buộc đã được ghi lại.

## Deployment Plan

- **Procedure Path**: `<path>`
- **Responsible Owner**: `<person-or-agent-id>`
- **Start Criteria**: `<observable-criteria>`
- **Success Criteria**: `<observable-criteria>`
- **Monitoring Window**: `<duration>`

## Rollback Plan

- **Trigger Criteria**: `<observable-thresholds>`
- **Procedure Path**: `<path>`
- **Responsible Owner**: `<person-or-agent-id>`
- **Recovery Verification**: `<checks>`

## Deployment Outcome

- **Outcome**: `pending | succeeded | failed | rolled-back`
- **Evidence**: `<deployment-logs-dashboards-or-artifacts>`
- **Incidents or Regressions**: `<ids-or-none>`
- **Post-Release Verification**: `<checks-and-results>`

## Completion Criteria

- [ ] Kết quả triển khai và bằng chứng đã được ghi lại.
- [ ] Kiểm tra sau release đạt tiêu chí thành công, hoặc rollback đã hoàn tất thành công.
- [ ] Regression được ghi trong `.agent/intelligence/git-nexus/regression-log.md`.
- [ ] Trạng thái release khớp với kết quả triển khai.

## Forbidden Actions

- Không triển khai khi thiếu phê duyệt bắt buộc và bằng chứng sẵn sàng.
- Không đổi phạm vi release sau khi duyệt mà không có phê duyệt theo quy trình governance.
- Không đánh dấu `deployed` trước khi kiểm tra sau release.
- Không che giấu bằng chứng triển khai lỗi, rollback, sự cố hay regression.

## Output Requirements

- Lưu thành `.agent/reports/releases/REL-<number>.md`.
- Giữ nguyên mọi heading trong template này.
- Dùng link tương đối theo repo và đúng giá trị enum.
