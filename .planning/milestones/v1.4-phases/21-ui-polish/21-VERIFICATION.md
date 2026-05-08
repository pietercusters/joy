---
phase: 21-ui-polish
verified: 2026-05-08T13:00:00Z
status: human_needed
score: 6/7
overrides_applied: 0
human_verification:
  - test: "Launch the TUI with `uv run joy`, press Tab to cycle through all 5 panes (ProjectList, ProjectDetail, WorktreePane, TerminalPane, MRPane), and observe focus indicators"
    expected: "Border changes from dim ($surface-lighten-2) to accent color when each pane is focused. Highlighted row shows full accent background when pane is focused, dimmed 30% accent when pane is NOT focused. Behavior is consistent across all 5 panes."
    why_human: "CSS :focus/:focus-within visual behavior requires runtime TUI observation — cannot be verified programmatically. Plan 02 Task 2 is explicitly marked checkpoint:human-verify gate=blocking. The summary auto-approved it in autonomous mode, which does not satisfy the gate."
---

# Phase 21: UI Polish — Verification Report

**Phase Goal:** All four panes render with consistent spacing, alignment, truncation, and focus indicators — visual bugs identified and fixed after architecture stabilization
**Verified:** 2026-05-08T13:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A documented audit checklist exists covering spacing, alignment, truncation, and focus indicators for all panes | VERIFIED | `21-RESEARCH.md` contains a 9-issue audit table with exact file/line locations for ProjectList, ProjectDetail, WorktreePane, TerminalPane, MRPane |
| 2 | Every bug identified in the audit is fixed — no known visual inconsistencies remain across the five panes | VERIFIED | All 9 CSS issues confirmed fixed in code (see Artifacts section); 9/9 pane layout tests pass |
| 3 | Focus indicators (border color, highlight styling) behave consistently when tabbing between panes | HUMAN NEEDED | CSS rules are in place and correct, but actual visual behavior requires runtime TUI observation — plan explicitly gates this as human-verify |
| 4 | All 5 focusable panes have self-contained border + focus CSS in DEFAULT_CSS | VERIFIED | Confirmed in all 5 widget files via direct code inspection |
| 5 | Every pane shows full-accent highlight row when the pane itself holds focus (both :focus and :focus-within variants present) | VERIFIED | All 5 panes have both variants confirmed |
| 6 | Section-spacer CSS rules are scoped to their parent widget in all panes | VERIFIED | No unscoped `.section-spacer` rules found anywhere in `src/joy/widgets/` |
| 7 | app.py CSS contains only grid layout rules — no per-widget border or focus rules | VERIFIED | `grep "#project-list\|#project-detail" app.py` returns no matches; only `#pane-grid` block present |

**Score:** 6/7 truths verified (1 requires human verification)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/joy/widgets/project_list.py` | Self-contained border, focus, focus-within CSS in DEFAULT_CSS | VERIFIED | Contains `ProjectList {`, `ProjectList:focus {`, `ProjectList:focus-within {`, `ProjectList:focus ProjectRow.--highlight`, `ProjectList .section-spacer` |
| `src/joy/widgets/project_detail.py` | Self-contained border, focus, focus-within CSS + scoped section-spacer + :focus highlight | VERIFIED | Contains `ProjectDetail:focus ObjectRow.--highlight` (line 88), `ProjectDetail:focus {` (line 79), `ProjectDetail .section-spacer` (line 94) |
| `src/joy/widgets/worktree_pane.py` | :focus row highlight variant added | VERIFIED | `WorktreePane:focus WorktreeRow.--highlight` at line 268 |
| `src/joy/widgets/terminal_pane.py` | :focus row highlight variant added | VERIFIED | `TerminalPane:focus SessionRow.--highlight` at line 207 |
| `src/joy/widgets/mr_pane.py` | :focus row highlight + scoped section-spacer | VERIFIED | `MRPane:focus MRRow.--highlight` at line 197; `MRPane .section-spacer` at line 203 |
| `src/joy/app.py` | Clean grid-only CSS with no widget-specific rules | VERIFIED | CSS block contains only `#pane-grid` — no `#project-list` or `#project-detail` rules |
| `tests/__snapshots__/test_snapshots/test_snapshot_initial_render.svg` | Updated SVG baseline for initial render | VERIFIED | File exists; snapshot tests pass (3/3) |
| `tests/__snapshots__/test_snapshots/test_snapshot_project_selected.svg` | Updated SVG baseline for project selected state | VERIFIED | File exists; regenerated in commit c779800 |
| `tests/__snapshots__/test_snapshots/test_snapshot_sync_active.svg` | Updated SVG baseline for sync active state | VERIFIED | File exists; regenerated in commit c779800 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `project_list.py` | Textual focus chain | DEFAULT_CSS `:focus` and `:focus-within` pseudo-classes | WIRED | Pattern `ProjectList:focus` confirmed in source |
| `project_detail.py` | Textual focus chain | DEFAULT_CSS `:focus` and `:focus-within` pseudo-classes | WIRED | Pattern `ProjectDetail:focus` confirmed in source |
| `app.py` | `project_list.py` | CSS no longer defines ProjectList borders — widget is self-contained | WIRED | Manual verification: `#project-list` absent from `app.py`; `ProjectList { border: ... }` present in `project_list.py` DEFAULT_CSS |
| `app.py` | `project_detail.py` | CSS no longer defines ProjectDetail borders — widget is self-contained | WIRED | Manual verification: `#project-detail` absent from `app.py`; `ProjectDetail { border: ... }` present in `project_detail.py` DEFAULT_CSS |

Note: gsd-tools key-link verification for plan 02 returned false for the "absence" patterns — this is a tool limitation (it cannot search for absence). Manual verification confirms both links are correctly wired.

### Data-Flow Trace (Level 4)

Not applicable. This phase contains only CSS changes — no dynamic data rendering added or modified. All modified files are styling-only.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Pane layout tests pass (all 9 CSS issue fixes verified) | `uv run pytest tests/test_pane_layout.py -x -q` | 9 passed | PASS |
| Snapshot baselines match corrected CSS state | `uv run pytest tests/test_snapshots.py -m snapshot -x -q` | 3 snapshots passed | PASS |
| Full test suite (excluding pre-existing failure) | `uv run pytest -x -q --ignore=tests/test_refresh.py` | 473 passed, 39 deselected | PASS |
| Visual focus indicator behavior | `uv run joy` + Tab cycle | Cannot verify programmatically | SKIP — human needed |

Pre-existing failure: `tests/test_refresh.py::test_terminal_load_on_mount` — confirmed pre-existing (documented in 21-02-SUMMARY.md, not caused by this phase).

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| UIPOL-01 | 21-01-PLAN, 21-01-SUMMARY | Systematic audit of all panes for visual inconsistencies | SATISFIED | `21-RESEARCH.md` documents 9-issue audit with severity, location, and fix prescription for each |
| UIPOL-02 | 21-01-PLAN, 21-02-PLAN, both SUMMARYs | Identified UI bugs fixed across all 5 panes | SATISFIED (programmatic) / HUMAN NEEDED (visual runtime) | All 9 CSS fixes confirmed in code; visual runtime behavior requires human verification |

Both requirement IDs from both plan frontmatter are accounted for. No orphaned requirements found.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/joy/widgets/worktree_pane.py` | 292 | "placeholder" in docstring | Info | Not a stub — describes initial loading widget, not empty implementation |
| `src/joy/widgets/terminal_pane.py` | 235 | "placeholder" in docstring | Info | Not a stub — describes initial loading widget |
| `src/joy/widgets/terminal_pane.py` | 468, 496 | "placeholder" in input widget param | Info | Not a stub — NameInputModal placeholder text, correct UI usage |

No blockers or warnings from anti-pattern scan on phase-modified files. The "placeholder" hits are all docstrings or UI input placeholders, not stub implementations — all have real data-fetching implementations behind them.

Code review (21-REVIEW.md) found 5 warnings and 6 info items in reviewed files. None block the phase goal (all are pre-existing logic concerns: `_update_highlight` emit guard, bare `except` in `_rebuild`, `_render_generation` init pattern, ribbon-width formula, None guard in `action_force_delete_object`). These are candidates for a future phase.

### Human Verification Required

#### 1. Visual Focus Indicator Consistency

**Test:** Run `cd /Users/pieter/Github/joy && uv run joy` to launch the TUI. Press Tab to cycle through all 5 panes: ProjectList, ProjectDetail, WorktreePane, TerminalPane, MRPane. For each pane:
1. Observe that the border changes from dim (grey) to accent color when the pane receives focus
2. If a project is selected (select with Enter), verify the highlighted row shows full accent background when the pane is focused
3. Tab to the next pane and verify the previously-focused pane's highlighted row reverts to dimmed (30% opacity) accent
4. Cycle through all 5 panes and confirm consistent behavior

**Expected:** All 5 panes show identical focus indicator behavior — accent border on focus, full-accent highlight row when focused, 30% highlight when not focused. No pane behaves differently from the others.

**Why human:** CSS `:focus` and `:focus-within` pseudo-class behavior is a runtime TUI property that cannot be verified by static code analysis. Snapshot tests capture a single state (initial render / project selected / sync active) but do not cover the dynamic focus-switching behavior that is the core goal of this phase. Plan 02 Task 2 explicitly marks this as a blocking human checkpoint.

### Gaps Summary

No gaps found. All programmatically verifiable must-haves are satisfied. The only open item is the human visual verification of focus indicator behavior at runtime — this is expected by the phase design (plan 02 is `autonomous: false` and contains a `checkpoint:human-verify gate="blocking"` task).

---

_Verified: 2026-05-08T13:00:00Z_
_Verifier: Claude (gsd-verifier)_
