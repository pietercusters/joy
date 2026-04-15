---
phase: 16-live-data-propagation
plan: "02"
subsystem: visual-stale
tags: [css, widgets, propagation, stale, object-row]
dependency_graph:
  requires: [16-01]
  provides: [ObjectRow.--stale, _render_project stale class application, TestStaleCSSIntegration]
  affects: [src/joy/widgets/object_row.py, src/joy/widgets/project_detail.py, tests/test_propagation.py]
tech_stack:
  added: []
  patterns: [textual-css-modifier-class, getattr-safety-default]
key_files:
  created: []
  modified:
    - src/joy/widgets/object_row.py
    - src/joy/widgets/project_detail.py
    - tests/test_propagation.py
decisions:
  - "getattr(item, 'stale', False) used in _render_project for backward-compatibility safety — avoids AttributeError if any legacy ObjectItem lacks the stale field"
  - "CSS modifier class --stale dims all three columns (icon, value, kind) with $text-muted color plus italic on value/kind — visually communicates stale state without removing the row"
metrics:
  duration: "~15min"
  completed: "2026-04-15"
  tasks_completed: 1
  tasks_pending: 1
  files_modified: 3
---

# Phase 16 Plan 02: Stale Visual Styling — Summary

**One-liner:** ObjectRow.--stale CSS class (dim+italic) added and applied via getattr-guarded add_class() in ProjectDetail._render_project during row construction.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add --stale CSS and apply during rendering | 0c1cfb0 | src/joy/widgets/object_row.py, src/joy/widgets/project_detail.py, tests/test_propagation.py |

## Tasks Pending

| Task | Name | Status | Reason |
|------|------|--------|--------|
| 2 | Human verify complete propagation flow | awaiting-human | checkpoint:human-verify — requires live TUI testing |

## What Was Built

### ObjectRow.--stale CSS (object_row.py)

Three CSS rules added to `DEFAULT_CSS` inside `ObjectRow`:
- `ObjectRow.--stale .col-value` — italic text, $text-muted color
- `ObjectRow.--stale .col-icon` — $text-muted color
- `ObjectRow.--stale .col-kind` — italic text, $text-muted color

All three columns dim together when the row has the `--stale` modifier class, visually communicating that the agent session is no longer active (PROP-04).

### Stale class application in _render_project (project_detail.py)

After creating each `ObjectRow`, a `getattr(item, 'stale', False)` check triggers `row.add_class("--stale")`. The `getattr` with default `False` provides backward-compatible safety (PROP-05).

Full block pattern:
```python
row = ObjectRow(item, index=row_index)
if getattr(item, 'stale', False):
    row.add_class("--stale")
scroll.mount(row)
```

When `_propagate_agent_stale()` marks an AGENTS object stale, the next `set_project()` call (triggered by `_propagate_changes()`) rebuilds the pane and the `--stale` class is re-applied automatically.

### TestStaleCSSIntegration (test_propagation.py)

4 new unit tests confirming:
1. `stale=True` item → row gets `--stale` class
2. `stale=False` item → row does NOT get `--stale` class
3. `stale` unset (default) → row does NOT get `--stale` class
4. Mixed stale/non-stale items → only stale rows get class

Tests use Textual's `add_class`/`has_class` which work without a running app.

## Verification Results

```
uv run pytest tests/test_propagation.py tests/test_object_row.py -x -q   # 41 passed
uv run pytest tests/ -x -q                                                # 309 passed, 38 deselected
```

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. The stale CSS class is fully wired from the `stale` field (set by `_propagate_agent_stale`) through to `add_class("--stale")` in `_render_project`. No placeholder data.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes. The `--stale` CSS class is a purely cosmetic rendering change with no trust boundary implications (T-16-05: accepted).

## Self-Check: PASSED

- src/joy/widgets/object_row.py: FOUND ObjectRow.--stale rules (3 CSS blocks)
- src/joy/widgets/project_detail.py: FOUND add_class("--stale") and getattr(item, 'stale', False)
- tests/test_propagation.py: FOUND TestStaleCSSIntegration (4 tests)
- Commit 0c1cfb0: FOUND in git log
- Full test suite: 309 passed
