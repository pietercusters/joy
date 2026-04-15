---
phase: quick
plan: 260415-mh6
subsystem: worktree-pane
tags: [refactor, worktree, ide-open, keyboard-bindings]
dependency_graph:
  requires: []
  provides: [worktree-ide-open, worktree-enter-key, worktree-unlinked-indicator]
  affects: [src/joy/app.py, src/joy/widgets/worktree_pane.py]
tech_stack:
  added: []
  patterns: [lazy-local-import, work-thread-worker, css-class-toggle]
key_files:
  created: []
  modified:
    - src/joy/app.py
    - src/joy/widgets/worktree_pane.py
    - tests/test_worktree_pane_cursor.py
decisions:
  - Enter key always opens IDE (never MR URL) — single code path via action_open_ide
  - CSS-only dim for unlinked worktrees (Option A) — no DOM rebuild needed
  - self.notify called directly in @work(thread=True) worker, matching _copy_branch pattern
metrics:
  duration: ~8 minutes
  completed: 2026-04-15
  tasks_completed: 2
  files_modified: 3
---

# Phase quick Plan 260415-mh6: Worktree IDE-Open Refactor Summary

**One-liner:** Collapsed two broken IDE-open paths into one correct path: `action_open_ide` reads `WorktreePane._rows[_cursor].path` directly; Enter delegates to it; unlinked rows get `--unlinked` CSS dim class.

## What Was Changed

### src/joy/app.py

- **`action_open_ide` rewritten:** Replaced `_open_first_of_kind(PresetKind.WORKTREE)` (which routed through project object lookup — often missing, always wrong) with direct `WorktreePane._rows[_cursor].path` read. Uses a lazy local import of WorktreePane to avoid circular imports.
- **`_open_worktree_path` worker added:** `@work(thread=True, exit_on_error=False)` worker that checks `Path(path).exists()` before calling `subprocess.run(["open", "-a", ide, path])`. Missing path triggers `notify(severity="warning")` instead of silent failure (threat T-mh6-02 mitigated).
- **`_update_worktree_link_status` method added:** Reads `_rel_index._project_for_wt_path` and `_rel_index._project_for_wt_branch` keys to compute linked sets, then calls `pane.set_linked_paths(linked_paths, linked_branches)`.
- **`_maybe_compute_relationships` updated:** Calls `_update_worktree_link_status()` after `_propagate_changes()`.
- **`_PANE_HINTS["worktrees-pane"]`** changed from `""` to `"i/Enter: Open IDE"`.

### src/joy/widgets/worktree_pane.py

- **`action_activate_row` rewritten:** Removed MR URL branch and inline `subprocess.run`. New body is a 3-line guard + `self.app.action_open_ide()` delegate. Both Enter and `i` now use the same code path.
- **`set_linked_paths(linked_paths, linked_branches)` method added:** Iterates `_rows`, adds/removes `--unlinked` CSS class based on path or `(repo_name, branch)` membership in the linked sets.
- **`WorktreeRow.--unlinked` CSS rule added** to `DEFAULT_CSS`: `color: $text-muted; text-style: dim` — dim styling without DOM rebuild.
- **Imports cleaned up:** `import subprocess` and `import webbrowser` removed (both were only used in the old `action_activate_row`).

### tests/test_worktree_pane_cursor.py

Updated three tests that validated old behavior:
- `test_enter_opens_mr_url` → renamed `test_enter_always_opens_ide_even_with_mr`: verifies `action_open_ide` is called even when row has an MR, via a test-app override.
- `test_enter_opens_ide_when_no_mr` → rewritten to patch `action_open_ide` on the app instead of `subprocess` on the module.
- `test_enter_noop_when_no_rows` → rewritten to assert `action_open_ide` not called instead of patching removed module attributes.

## Bug Root Causes Fixed

**Bug 1 — Wrong WORKTREE object lookup:** `action_open_ide` called `_open_first_of_kind(PresetKind.WORKTREE)` which searched the active project's objects for a `WORKTREE`-kind entry. This entry is often absent (not all projects have a WORKTREE object) and when present holds a path from config time that may be stale. The pane already has the correct live path from `git worktree list` in `WorktreeRow.path`.

**Bug 2 — MR URL priority in Enter:** `action_activate_row` gave priority to `mr_info.url` when present, opening the browser instead of the IDE. Developers in the Worktrees pane expecting Enter to open their editor got taken to a web browser tab instead.

## New set_linked_paths Hook

`JoyApp._update_worktree_link_status()` is called from `_maybe_compute_relationships()` (after both worktree and terminal data are ready and `RelationshipIndex` is computed). It extracts the set of linked worktree paths and `(repo_name, branch)` pairs from `_rel_index`, then calls `WorktreePane.set_linked_paths()`. The pane iterates its rows and applies/removes the `--unlinked` CSS class. No DOM rebuild — CSS class toggle only.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated tests that validated removed behavior**
- **Found during:** Task 2 verification (test suite run)
- **Issue:** Three tests patched `joy.widgets.worktree_pane.webbrowser` and `joy.widgets.worktree_pane.subprocess` — both imports were removed. Tests asserted old MR-URL and inline-subprocess behavior.
- **Fix:** Rewrote tests to verify the new delegation pattern (`action_open_ide` called on app) using a test-app subclass override. Test count: 309 → 323 passing.
- **Files modified:** `tests/test_worktree_pane_cursor.py`
- **Commit:** 6c4cc52

## Edge Cases Noted

- `_update_worktree_link_status` is called after both data sources are ready (the two-flag gate in `_maybe_compute_relationships`). On the first load, if only worktrees arrive before sessions, `_rel_index` is still `None` and the method returns early without marking anything — correct behavior since rows are also being populated for the first time.
- `set_linked_paths` is additive/idempotent: if called with an empty set, all rows get `--unlinked`. This is intentional — a worktree with no matching project is genuinely unlinked.
- The `self.notify` call in `_open_worktree_path` matches the pattern in `_copy_branch` and `_do_open_global` (called directly, not via `call_from_thread`). Textual's `@work(thread=True)` workers post events safely when calling reactive methods on `self`.

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, or trust boundaries introduced.

## Self-Check: PASSED

- `src/joy/app.py` modified: confirmed
- `src/joy/widgets/worktree_pane.py` modified: confirmed
- `tests/test_worktree_pane_cursor.py` modified: confirmed
- Commit 6c4cc52 exists: confirmed
- 323 tests passing, 0 failures
