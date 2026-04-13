---
phase: 12-iterm2-integration-terminal-pane
plan: "02"
subsystem: terminal-pane-widget
tags: [tui, widgets, terminal, navigation, iterm2]
requirements: [TERM-01, TERM-02, TERM-03, TERM-04]

dependency_graph:
  requires:
    - "src/joy/models.py (TerminalSession dataclass)"
    - "src/joy/terminal_sessions.py (activate_session stub)"
  provides:
    - "src/joy/widgets/terminal_pane.py (TerminalPane, SessionRow, GroupHeader)"
    - "tests/test_terminal_pane.py (30 tests)"
  affects:
    - "src/joy/app.py (will use set_sessions() in Plan 12-03)"
    - "tests/test_pane_layout.py (updated to reflect Phase 12 loading state)"

tech_stack:
  added: []
  patterns:
    - "Lazy module import in worker thread for mockable activate_session"
    - "VerticalScroll(can_focus=False) for non-focusable scroll container"
    - "GroupHeader(Static) duplicated from worktree_pane (avoids cross-widget coupling)"
    - "TDD: RED commit then GREEN commit with separate commits"

key_files:
  created:
    - src/joy/widgets/terminal_pane.py
    - tests/test_terminal_pane.py
    - src/joy/terminal_sessions.py
  modified:
    - src/joy/models.py
    - tests/test_models.py
    - tests/test_pane_layout.py

decisions:
  - "Use 'import joy.terminal_sessions as _ts; _ts.activate_session()' pattern (not 'from' import) in worker thread to allow mock patching at module level in tests"
  - "Stub terminal_sessions.py created to satisfy imports (Plan 12-01 owns real implementation)"
  - "models.py updated with full dataclasses (Repo, WorktreeInfo, MRInfo, detect_forge) from phases 6-11 to fix worktree isolation gap"
  - "test_pane_layout.py updated: stub 'coming soon' check replaced with loading-state check that accepts both 'loading' and 'coming soon'"

metrics:
  duration: "~20 minutes"
  completed: "2026-04-13T17:04:56Z"
  tasks_completed: 1
  files_modified: 6
---

# Phase 12 Plan 02: TerminalPane Widget Implementation Summary

Full TerminalPane widget with SessionRow rendering, Claude/Other session grouping, cursor navigation (j/k/up/down/Enter/Escape), empty/unavailable states, scroll preservation, and refresh label.

## What Was Built

### Core Widget: `src/joy/widgets/terminal_pane.py`

**Constants (per D-07):**
- `ICON_SESSION = "\uf120"` — nf-fa-terminal for non-Claude sessions
- `ICON_CLAUDE = "\U000f1325"` — nf-md-robot for Claude sessions
- `INDICATOR_BUSY = "\u25cf"` — filled circle for active Claude session
- `INDICATOR_WAITING = "\u25cb"` — empty circle for idle session

**Classes:**
- `_TerminalScroll(VerticalScroll, can_focus=False)` — non-focusable scroll container
- `GroupHeader(Static)` — section header (duplicated from worktree_pane, no coupling)
- `SessionRow(Static)` — single-line row with session_id attribute for Enter activation
- `TerminalPane(Widget, can_focus=True)` — main interactive pane

**TerminalPane behavior:**
- `set_sessions(sessions)` — groups Claude (foreground=='claude') under 'Claude' header, others under 'Other', both sorted alphabetically by session_name
- `set_sessions(None)` — shows 'iTerm2 unavailable' empty state
- `set_sessions([])` — shows 'No terminal sessions' empty state
- Empty groups omitted (no Claude sessions = no 'Claude' header)
- Scroll position preserved across rebuilds via `call_after_refresh`
- Cursor navigation via `_cursor` int tracking `_rows: list[SessionRow]`
- Enter key calls `activate_session(session_id)` in background worker thread (`@work(thread=True)`)
- Escape key returns focus to `#project-list > #project-listview`
- `set_refresh_label(timestamp, stale=False)` updates border_title

### Test Suite: `tests/test_terminal_pane.py`

30 tests covering:
- Constants verification
- SessionRow: session_id storage, content (name, icon, indicators, process, cwd)
- TerminalPane bindings (escape, up, down, k, j, enter all present)
- Initial state (_cursor=-1, _rows=[])
- set_sessions grouping and rendering (Claude/Other headers, row counts)
- Empty/unavailable states
- Cursor navigation with bounds clamping
- Enter key activation via mock at joy.terminal_sessions module level
- Enter no-op when _cursor=-1
- set_refresh_label with and without stale warning
- Scroll preservation (no crash across rebuilds)
- Alphabetical sorting in both groups

### Supporting Files

- `src/joy/terminal_sessions.py` — stub (Plan 12-01 owns real implementation). Provides the `activate_session(session_id) -> bool` interface
- `src/joy/models.py` — updated with full dataclasses from phases 6-11 (Repo, WorktreeInfo, MRInfo, detect_forge) to fix worktree isolation gap

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test used `.renderable` attribute instead of `.content`**
- **Found during:** GREEN phase, first test run
- **Issue:** Tests used `str(row.renderable)` but Textual's Static widget exposes content as `.content`, not `.renderable`
- **Fix:** Changed all test assertions to use `.content` (matches existing test_worktree_pane.py pattern)
- **Files modified:** tests/test_terminal_pane.py
- **Commit:** 5980ef6 (updated in place before GREEN commit)

**2. [Rule 1 - Bug] activate_session mock target was wrong**
- **Found during:** GREEN phase test run
- **Issue:** `patch("joy.widgets.terminal_pane.activate_session")` fails because the function is imported lazily inside `_do_activate` using `import joy.terminal_sessions as _ts`, not a module-level import
- **Fix:** Changed implementation to use module-reference call `_ts.activate_session()` instead of `from ... import`; changed test mock target to `joy.terminal_sessions.activate_session`
- **Files modified:** src/joy/widgets/terminal_pane.py, tests/test_terminal_pane.py
- **Commit:** fd400ce

**3. [Rule 3 - Blocking] Worktree isolation: missing models dataclasses**
- **Found during:** Full suite run
- **Issue:** This worktree was reset to commit `1ab4ab9` which had `TerminalSession` in models.py but NOT `Repo`, `WorktreeInfo`, `MRInfo`, `detect_forge` (added in phases 6-11). Test files for those phases exist at HEAD but couldn't run.
- **Fix:** Added full models.py content from main repo (all phases) to make worktree self-contained. Updated test_models.py to expect new Config fields.
- **Files modified:** src/joy/models.py, tests/test_models.py
- **Commit:** fd400ce

**4. [Rule 1 - Bug] test_pane_layout.py expected stub 'coming soon' text**
- **Found during:** Full suite run after implementing TerminalPane
- **Issue:** `test_stub_panes_show_coming_soon` asserted `"coming soon"` in TerminalPane, but Plan 12-02 replaces the stub with a real implementation that shows "Loading..."
- **Fix:** Updated test to accept either "loading" or "coming soon" and renamed it to `test_terminal_pane_shows_loading_state`
- **Files modified:** tests/test_pane_layout.py
- **Commit:** fd400ce

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 5980ef6 | test | RED: failing tests for TerminalPane widget + models.py + stub terminal_sessions.py |
| fd400ce | feat | GREEN: full TerminalPane implementation, all 30 tests pass, full suite green |

## Known Stubs

`src/joy/terminal_sessions.py`: Stub created by this plan to satisfy imports. The real implementation (using iterm2 Python API) is owned by Plan 12-01. The stub returns `None` from `fetch_sessions()` and `False` from `activate_session()`. Plan 12-01 will replace this file entirely.

## Threat Surface Scan

No new network endpoints or auth paths introduced. `action_focus_session` runs in `@work(thread=True, exit_on_error=False)` per T-12-04 mitigation. All data displayed is local session info only (T-12-05 accepted).

## Self-Check: PASSED

Files created/modified:
- FOUND: src/joy/widgets/terminal_pane.py
- FOUND: tests/test_terminal_pane.py
- FOUND: src/joy/terminal_sessions.py
- FOUND: src/joy/models.py (updated)

Commits:
- FOUND: 5980ef6
- FOUND: fd400ce

Test results: 30/30 terminal pane tests pass, 274/274 full suite tests pass.
