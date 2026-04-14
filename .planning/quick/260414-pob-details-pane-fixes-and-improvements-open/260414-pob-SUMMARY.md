# Quick Task 260414-pob Summary

**Task:** Details pane fixes and improvements: open icon, legend dismiss, new grouping, repo as object, indent all panes
**Date:** 2026-04-14
**Status:** Complete (with orchestrator post-processing to fix executor regressions)

## What Was Done

### Bug Fix 1: Open indicator restored
- `ObjectRow` restored to `Horizontal` 3-column layout (col-icon, col-value, col-kind)
- `_build_icon_text()` static method added: renders dot indicator (● filled / ○ empty) + preset icon in col-icon
- `REPO` kind added to `PRESET_ICONS` with nf-oct-repo glyph (`\uf401`)

### Bug Fix 2: Legend `l`-key dismiss
- `action_legend()` in `app.py` now toggles: checks screen stack for existing `LegendModal`, dismisses if found, pushes new one otherwise
- No more stacking on double-press

### New: Semantic grouping in Details pane
- `GROUP_ORDER` + `GROUP_LABELS` replaced with `SEMANTIC_GROUPS` (3 groups):
  - **Code**: repo, worktrees, mrs, branches
  - **Docs**: tickets, notes, urls, files, threads
  - **Agents**: agents
- Both `project_detail.py` and `app.py` updated

### New: Repo as proper Project object
- `PresetKind.REPO` added to `models.py`
- Repo is synthesized as `ObjectItem(kind=PresetKind.REPO, ...)` inside `_render_project()` — rendered through the same `ObjectRow` path as all other objects
- Removed the special-cased `Static` overview row
- `preset_picker.py` excludes `REPO` from the user-addable picker

### New: Consistent indent in all panes
- `terminal_pane.py` `SessionRow` rows now have ` ` (1-space) leading indent matching worktree style

### Legend expanded
- Added Worktree Pane and Terminal Pane icon sections to `LegendModal`

## Commits (from executor + orchestrator fixes)

- `902aa14` test(quick-260414-pob): add failing tests for LegendModal
- `2531a97` feat(quick-260414-pob): create LegendModal and add toggle l-key binding
- `b39bf2d` feat(quick-260414-pob): semantic grouping, repo as object, consistent indent
- Orchestrator: restored `MRInfo.url` field, `worktree_pane.py` cursor navigation, `test_worktree_pane_cursor.py`, updated `object_row.py` and tests for column layout

## Test Results

285 tests pass, 0 failures, 0 regressions.
