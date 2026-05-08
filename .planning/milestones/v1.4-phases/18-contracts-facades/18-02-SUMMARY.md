---
phase: 18-contracts-facades
plan: 02
status: complete
started: 2026-05-08
completed: 2026-05-08
---

# Plan 18-02 Summary: App & Resolver Facades

## What was built
Added public facade properties and methods to JoyApp and RelationshipIndex, creating the public API surface that widgets will call instead of private attributes.

## Key files

### Modified
- `src/joy/app.py` — 3 properties (projects, config, current_worktrees) + 7 methods (save_projects, close_tab, append_to_archive, remove_from_archive, refresh_terminal, start_add_object_loop, update_badges)
- `src/joy/resolver.py` — 2 properties (linked_worktree_paths, linked_worktree_branches) on RelationshipIndex

## Deviations
None. All additions are thin wrappers over existing private methods — no logic change.

## Self-Check: PASSED
- All 10 JoyApp facade items present
- Both RelationshipIndex properties present
- All 402 existing tests pass
