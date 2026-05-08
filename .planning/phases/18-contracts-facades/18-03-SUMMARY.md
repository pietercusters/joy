---
phase: 18-contracts-facades
plan: 03
status: complete
started: 2026-05-08
completed: 2026-05-08
---

# Plan 18-03 Summary: Replace Private Access & Contract Tests

## What was built
Replaced all 30+ private cross-boundary accesses with public facade calls. Created contract verification tests for all 5 Protocol classes.

## Key files

### Created
- `tests/test_ports.py` — 9 tests: structural conformance for all 5 Protocols, rejection tests, ARCH-01 enforcement

### Modified
- `src/joy/app.py` — Uses project_list.current_project, detail.current_project, detail.default_items, pane.highlighted_worktree, rel_index.linked_worktree_paths/branches
- `src/joy/widgets/project_detail.py` — Uses self.app.config, self.app.start_add_object_loop, self.app.projects
- `src/joy/widgets/project_list.py` — Uses self.app.projects, self.app.save_projects, self.app.close_tab, self.app.append_to_archive, self.app.remove_from_archive, self.app.current_worktrees, self.app.update_badges, detail.clear()
- `src/joy/widgets/terminal_pane.py` — Uses self.app.refresh_terminal

## Deviations
- Fixed defensive config access in `_build_virtual_rows` — test apps may not have `config` property, so added `getattr` guard matching the original defensive pattern.

## Self-Check: PASSED
- `grep -rn 'self.app._' src/joy/widgets/` returns 0 matches
- `grep -rn 'from joy.ports' src/joy/widgets/` returns 0 matches (ARCH-01)
- `grep -rn 'detail._project|pane._cursor' src/joy/app.py` returns 0 matches
- All 402 existing tests pass
- All 9 contract tests pass (test_ports.py)
