---
phase: quick-260420-izh
verified: 2026-04-20T12:00:00Z
status: human_needed
score: 6/6 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 5/6
  gaps_closed:
    - "When a sync succeeds (pane finds a match), the dimmed state is cleared — normal yellow fill restores"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Select a project with no worktrees, then select a project with worktrees"
    expected: "WorktreePane highlight restores from muted/dim to yellow accent fill when project has worktrees; stays muted when project has none"
    why_human: "CSS specificity rule WorktreePane.--dim-selection:focus-within is correct in code but visual cascade cannot be confirmed without running the TUI"
  - test: "Press Enter/o in a dimmed WorktreePane"
    expected: "Toast 'No worktree for this project' appears; IDE does not open"
    why_human: "Toast and guard logic verified in code; runtime TUI behavior needs visual confirmation"
  - test: "Press Enter in a dimmed TerminalPane"
    expected: "Toast 'No terminal for this project' appears; session is not activated"
    why_human: "Toast and guard logic verified in code; runtime TUI behavior needs visual confirmation"
---

# Quick Task 260420-izh: Pane Sync Dimmed Selection — Re-Verification

**Task Goal:** Pane sync behavior redesign — dimmed selection + scoped open in joy TUI.
**Verified:** 2026-04-20T12:00:00Z
**Status:** human_needed
**Re-verification:** Yes — after CSS :not() fix

## Re-Verification Summary

Previous gap: CSS used `WorktreePane:focus-within:not(.--dim-selection)` and `TerminalPane:focus-within:not(.--dim-selection)`, which Textual 8.x does not support. This caused 74 unit tests to fail with CSS tokenizer errors.

Fix applied (commit `675450f`): `:not()` rules replaced with a two-rule pattern:
1. Plain `WorktreePane:focus-within WorktreeRow.--highlight { background: $accent; }` — original rule unchanged, restores yellow fill on match
2. `WorktreePane.--dim-selection:focus-within WorktreeRow.--highlight { background: transparent; ... }` — higher-specificity override keeps row dim when `--dim-selection` class is present and pane has focus

Same pattern applied to `TerminalPane`. No `:not()` pseudo-class appears anywhere in either file.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | When a project is selected and has no worktrees, WorktreePane shows a dimmed border outline (no fill) on its highlighted row | VERIFIED | `set_dimmed(True)` called in `_sync_from_project` when no worktrees exist; `WorktreePane.--dim-selection WorktreeRow.--highlight { background: transparent; ... }` at line 272 of worktree_pane.py |
| 2 | When a project is selected and has no terminals, TerminalPane shows a dimmed border outline (no fill) on its highlighted row | VERIFIED | `set_dimmed(True)` called in `_sync_from_project` when no terminals exist; `TerminalPane.--dim-selection SessionRow.--highlight { background: transparent; ... }` at line 220 of terminal_pane.py |
| 3 | Pressing Enter/o in a dimmed WorktreePane shows 'No worktree for this project' toast instead of opening | VERIFIED | `action_activate_row` guards on `self._is_dimmed` and calls `self.app.notify("No worktree for this project", markup=False)` |
| 4 | Pressing Enter/o in a dimmed TerminalPane shows 'No terminal for this project' toast instead of opening | VERIFIED | `action_focus_session` guards on `self._is_dimmed` and calls `self.app.notify("No terminal for this project", markup=False)` |
| 5 | Selecting from WorktreePane or TerminalPane also drives dimmed state on the other panes that cannot match | VERIFIED | `_sync_from_worktree` and `_sync_from_session` both call `set_dimmed()` on the other pane based on `sync_to()` return value |
| 6 | When a sync succeeds (pane finds a match), the dimmed state is cleared — normal yellow fill restores | VERIFIED | `set_dimmed(False)` removes `--dim-selection` class; plain `WorktreePane:focus-within WorktreeRow.--highlight { background: $accent; }` rule at line 262 then applies without the higher-specificity dim override. No `:not()` in codebase. CSS parse error resolved — unit tests pass. |

**Score:** 6/6 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/joy/widgets/worktree_pane.py` | sync_to() returns bool; _is_dimmed attr; set_dimmed() method; --dim-selection CSS; action_activate_row guard | VERIFIED | All present; CSS uses valid Textual pseudo-classes only |
| `src/joy/widgets/terminal_pane.py` | sync_to() returns bool; _is_dimmed attr; set_dimmed() method; --dim-selection CSS; action_focus_session guard | VERIFIED | All present; CSS uses valid Textual pseudo-classes only |
| `src/joy/widgets/project_list.py` | sync_to() returns bool (uniform pattern) | VERIFIED | Returns True on match, False otherwise |
| `src/joy/app.py` | _sync_from_project/_sync_from_worktree/_sync_from_session read bool returns and call set_dimmed() | VERIFIED | All three methods fully implemented |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| app.py _sync_from_project | WorktreePane.set_dimmed / TerminalPane.set_dimmed | bool return from sync_to() | WIRED | `matched = wt_pane.sync_to(...); wt_pane.set_dimmed(not matched)` |
| WorktreePane.action_activate_row | self.app.notify | _is_dimmed guard | WIRED | `if self._is_dimmed: self.app.notify(...)` |
| TerminalPane.action_focus_session | self.app.notify | _is_dimmed guard | WIRED | `if self._is_dimmed: self.app.notify(...)` |

### Data-Flow Trace (Level 4)

Not applicable — this task modifies TUI state management (CSS class toggling and guard conditions), not data-fetching components.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Unit test suite passes (excluding pre-existing failures) | `uv run pytest tests/ -q --ignore=tests/tui` | 338 passed, 11 failed — all 11 failures are pre-existing (6 TestTerminalAutoRemove, 4 test_sync, 1 test_terminal_load_on_mount); 0 CSS tokenizer errors | PASS |
| No :not() pseudo-class in worktree_pane.py | `grep ':not(' src/joy/widgets/worktree_pane.py` | No matches | PASS |
| No :not() pseudo-class in terminal_pane.py | `grep ':not(' src/joy/widgets/terminal_pane.py` | No matches | PASS |

**Pre-existing failure baseline (from main branch commit 3e63734 and commit before CSS fix):**
- `TestTerminalAutoRemove` — 6 tests: `JoyApp._propagate_terminal_auto_remove` removed in a prior task (260416-of2), tests not yet updated
- `test_sync` — 4 tests: resolver returns 0 terminals for `PresetKind.TERMINALS` objects (pre-existing resolver behavior mismatch)
- `test_terminal_load_on_mount` — 1 test: fails on main branch before any izh work

Before the CSS fix, all of `test_refresh.py` (10+ tests) also failed with `textual.css.tokenizer` errors from the `:not()` pseudo-class. Those failures are now resolved.

### Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|---------|
| SYNC-01 | WorktreePane dimmed when no worktree match | SATISFIED | set_dimmed(True) + CSS background: transparent |
| SYNC-02 | TerminalPane dimmed when no terminal match | SATISFIED | set_dimmed(True) + CSS background: transparent |
| SYNC-03 | WorktreePane Enter/o guard shows toast | SATISFIED | action_activate_row guard on _is_dimmed |
| SYNC-04 | TerminalPane Enter guard shows toast | SATISFIED | action_focus_session guard on _is_dimmed |
| SYNC-05 | Cross-pane dim propagation from WorktreePane | SATISFIED | _sync_from_worktree calls set_dimmed on TerminalPane |
| SYNC-06 | Yellow fill restores on match | SATISFIED | CSS rule ordering + higher-specificity dim override replaces broken :not() |

### Anti-Patterns Found

None. The `:not()` blocker from the previous verification is resolved. No remaining CSS anti-patterns.

### Human Verification Required

All automated checks pass. The following items require visual confirmation in the running TUI:

#### 1. Dimmed State Visual Appearance

**Test:** Select a project that has no linked worktrees. Observe WorktreePane.
**Expected:** Highlighted row shows muted border/dim text (transparent background), NOT the yellow accent fill.
**Why human:** CSS class toggling is verified in code; visual rendering requires running `uv run joy`.

#### 2. Yellow Fill Restoration

**Test:** Select a project with no worktrees (dim state), then select a project that has worktrees.
**Expected:** WorktreePane highlight restores to yellow accent fill when `--dim-selection` class is removed.
**Why human:** The CSS specificity rule is correct but the cascade behavior at runtime needs visual confirmation.

#### 3. Toast on Dimmed Pane Open

**Test:** With a dimmed WorktreePane, press Enter or o. Repeat for TerminalPane.
**Expected:** Toast appears with "No worktree for this project" / "No terminal for this project". No open action occurs.
**Why human:** Action guard logic is code-verified; actual toast rendering and inhibition of open require TUI interaction.

### Gaps Summary

No gaps. The previous gap (`:not()` pseudo-class causing CSS parse errors) is fully resolved. All 6 truths are verified. Three human verification items remain for visual/interaction confirmation in the live TUI — these are normal human_needed items for a visual TUI task, not blockers.

---

_Verified: 2026-04-20T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
