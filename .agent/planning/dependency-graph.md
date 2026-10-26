---
id: dep-graph-v1
title: Dependency Graph
type: planning
domain: architecture
module: planning
tags: [dependencies, epics, milestones]
priority: 2
---
# Đồ thị phụ thuộc

## Purpose

Lưu các quan hệ phụ thuộc có hướng chính thức, ràng buộc thứ tự giữa roadmap item, milestone, epic và task.

## Status Model

- **Valid Edge Statuses**: `active | satisfied | blocked | removed`

## Dependency Records

| Edge ID | ID phụ thuộc | ID tiên quyết | Loại | Owner | Trạng thái | Bằng chứng | Governance link |
|---|---|---|---|---|---|---|---|

| `EDGE-001` | `M-002` | `M-001` | `milestone` | `trong-hung` | `active` | `.agent/planning/epics.md` | `none` |
| `EDGE-002` | `E-002` | `E-001` | `epic` | `trong-hung` | `active` | `.agent/planning/epics.md` | `none` |
| `EDGE-003` | `E-003` | `E-001` | `epic` | `trong-hung` | `active` | `.agent/planning/epics.md` | `none` |
| `EDGE-004` | `E-004` | `E-003` | `epic` | `trong-hung` | `active` | `.agent/planning/epics.md` | `none` |
| `EDGE-005` | `E-005` | `E-002` | `epic` | `trong-hung` | `active` | `.agent/planning/epics.md` | `none` |
| `EDGE-006` | `E-006` | `E-002` | `epic` | `trong-hung` | `active` | `.agent/planning/epics.md` | `none` |
| `EDGE-007` | `E-007` | `E-006` | `epic` | `trong-hung` | `active` | `.agent/planning/epics.md` | `none` |
| `EDGE-008` | `E-008` | `E-004` | `epic` | `trong-hung` | `active` | `.agent/planning/epics.md` | `none` |
| `EDGE-009` | `E-009` | `E-006` | `epic` | `trong-hung` | `active` | `.agent/planning/epics.md` | `none` |
| `EDGE-010` | `E-009` | `E-007` | `epic` | `trong-hung` | `active` | `.agent/planning/epics.md` | `none` |
| `EDGE-011` | `E-010` | `E-004` | `epic` | `trong-hung` | `active` | `.agent/planning/epics.md` | `none` |
| `EDGE-012` | `E-010` | `E-005` | `epic` | `trong-hung` | `active` | `.agent/planning/epics.md` | `none` |
| `EDGE-013` | `E-010` | `E-006` | `epic` | `trong-hung` | `active` | `.agent/planning/epics.md` | `none` |
| `EDGE-014` | `E-011` | `E-005` | `epic` | `trong-hung` | `active` | `.agent/planning/epics.md` | `none` |
| `EDGE-015` | `E-011` | `E-006` | `epic` | `trong-hung` | `active` | `.agent/planning/epics.md` | `none` |
| `EDGE-016` | `E-012` | `E-004` | `epic` | `trong-hung` | `active` | `.agent/planning/epics.md` | `none` |
| `EDGE-017` | `E-012` | `E-009` | `epic` | `trong-hung` | `active` | `.agent/planning/epics.md` | `none` |
| `EDGE-018` | `E-013` | `E-005` | `epic` | `trong-hung` | `active` | `.agent/planning/epics.md` | `none` |
| `EDGE-019` | `E-014` | `E-008` | `epic` | `trong-hung` | `active` | `.agent/planning/epics.md` | `none` |
| `EDGE-020` | `E-014` | `E-013` | `epic` | `trong-hung` | `active` | `.agent/planning/epics.md` | `none` |
| `EDGE-021` | `E-015` | `E-008` | `epic` | `trong-hung` | `active` | `.agent/planning/epics.md` | `none` |
| `EDGE-022` | `E-015` | `E-013` | `epic` | `trong-hung` | `active` | `.agent/planning/epics.md` | `none` |
| `EDGE-023` | `E-016` | `E-004` | `epic` | `trong-hung` | `active` | `.agent/planning/epics.md` | `none` |
