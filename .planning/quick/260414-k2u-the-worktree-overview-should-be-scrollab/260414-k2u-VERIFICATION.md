---
phase: quick-260414-k2u
verified: 2026-04-14T00:00:00Z
status: human_needed
score: 6/6 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Launch joy in a project with active worktrees. Tab to the Worktrees pane."
    expected: "Footer shows j/k/Enter/Esc binding hints when WorktreePane is focused."
    why_human: "Footer hint rendering is visual/runtime behavior — cannot verify without running the TUI."
  - test: "With Worktrees pane focused, press j and k."
    expected: "Cursor moves between worktree rows; the selected row highlights in accent color. GroupHeader rows (repo names) are skipped — cursor lands only on worktree entries."
    why_human: "CSS highlight rendering and scroll behavior require visual inspection in a running TUI."
  - test: "Press Enter on a worktree row that has an associated MR."
    expected: "Browser opens the MR URL (e.g., https://github.com/owner/repo/pull/N)."
    why_human: "Requires a live worktree with an open MR; cannot mock webbrowser in a running TUI session."
  - test: "Press Enter on a worktree row with no MR."
    expected: "The worktree path opens in the configured IDE (e.g., PyCharm or Cursor)."
    why_human: "Requires a live worktree without an MR and a configured IDE on the machine."
  - test: "Press Escape while Worktrees pane is focused."
    expected: "Focus returns to the project list pane on the left."
    why_human: "Focus transfer behavior requires visual inspection of the running TUI."
---

# Phase quick-260414-k2u: Worktree Pane Cursor Navigation Verification Report

**Phase Goal:** The Worktree overview should be scrollable exactly like the other panes. When hitting enter on an item, it should open the MR if there is one, or else the worktree in the set IDE.
**Verified:** 2026-04-14
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | Focusing WorktreePane shows j/k/Enter/Esc hints in the footer via BINDINGS | VERIFIED | `WorktreePane.BINDINGS` at worktree_pane.py:224-231 — contains escape, up, down, k, j, enter; Textual surfaces these as footer hints automatically |
| 2 | j/down moves cursor down, k/up moves cursor up — GroupHeader rows are skipped | VERIFIED | `action_cursor_down/up` at lines 370-378 step through `_rows`; `_rows` is built by appending only `WorktreeRow` instances (line 337); `GroupHeader` is mounted to DOM but never added to `_rows` (lines 329 vs 337) |
| 3 | Enter on a WorktreeRow with an MR opens the MR URL in the browser | VERIFIED | `action_activate_row` (line 383): when `mr_info is not None and mr_info.url` and scheme is http/https, calls `webbrowser.open(mr_info.url)`. Test `test_enter_opens_mr_url` passes |
| 4 | Enter on a WorktreeRow without an MR opens the worktree path in the configured IDE | VERIFIED | `action_activate_row` else branch (lines 393-399): `subprocess.run(["open", "-a", ide, row.path], check=False)` where `ide` comes from `self.app._config.ide`. Test `test_enter_opens_ide_when_no_mr` passes |
| 5 | Escape returns focus to the project list | VERIFIED | `action_focus_projects` (line 380): `self.app.query_one("#project-list").focus()` — bound to escape in BINDINGS |
| 6 | Cursor highlights the selected row using the --highlight CSS class | VERIFIED | `_update_highlight` (lines 363-368) removes `--highlight` from all rows then adds it to `_rows[self._cursor]` and calls `scroll_visible()`. CSS rule at line 252-256 renders accent background |

**Score:** 6/6 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/joy/models.py` | MRInfo with url field | VERIFIED | Line 161: `url: str = ""` — defaulted field, all existing callsites preserved |
| `src/joy/mr_status.py` | url populated for GitHub (pr['url']) and GitLab (mr.get('web_url', '')) | VERIFIED | Line 75: `--json` includes `url`. Line 103: `url=pr.get("url", "")`. Line 153: `url=mr.get("web_url", "")` |
| `src/joy/widgets/worktree_pane.py` | WorktreePane with cursor navigation and Enter handler | VERIFIED | BINDINGS, `_cursor`, `_rows`, `_update_highlight`, `action_cursor_up/down`, `action_focus_projects`, `action_activate_row` all present and substantive |
| `tests/test_worktree_pane_cursor.py` | Unit tests for cursor and Enter actions | VERIFIED | 7 test cases — all pass in 1.46s |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `WorktreePane.action_activate_row` | `webbrowser.open` | `row.mr_info.url` when truthy and http/https scheme | WIRED | Lines 388-392: `if mr_info is not None and mr_info.url: ... webbrowser.open(mr_info.url)` — module-level import, patchable, tested |
| `WorktreePane.action_activate_row` | `subprocess.run` | `row.path` when no mr_info or empty url | WIRED | Lines 393-399: else branch calls `subprocess.run(["open", "-a", ide, row.path])` — module-level import, patchable, tested |
| `WorktreePane._update_highlight` | `WorktreeRow.--highlight CSS class` | `_rows` list from `set_worktrees` | WIRED | Lines 363-368: iterates `_rows`, removes/adds `--highlight`; CSS rule at line 252-256 renders it |

**Note:** The plan's key_link pattern `subprocess\\.run.*open.*-a.*ide` uses "ide" as a substring — this matches the variable name `ide` in the actual call `subprocess.run(["open", "-a", ide, row.path])`. The gsd-tools key-link checker reported "Source file not found" because the `from` field used class method notation rather than a file path — manual verification confirms all three links are wired.

**Deviation (not a gap):** `action_activate_row` adds a `urlparse` scheme guard (`parsed.scheme in ("https", "http")`) before opening the browser. This is stricter than the plan's requirement ("when mr_info.url is truthy") — a security improvement, not a regression. URLs with non-http/https schemes are silently ignored rather than passed to the OS browser.

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|-------------------|--------|
| `worktree_pane.py WorktreeRow` | `mr_info.url` | `mr_data` dict passed to `set_worktrees` | Yes — populated by `fetch_mr_data` from `gh`/`glab` CLI output | FLOWING |
| `worktree_pane.py WorktreePane._rows` | `WorktreeRow` items | `set_worktrees` loop over `worktrees` list | Yes — real `WorktreeInfo` objects from `discover_worktrees` | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 7 cursor tests pass | `uv run pytest tests/test_worktree_pane_cursor.py -v` | 7 passed in 1.46s | PASS |
| Full fast suite passes (no regressions) | `uv run pytest -q` | 282 passed, 38 deselected, 0 failures | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| WKTR-CURSOR-01 | 260414-k2u-PLAN.md | Cursor navigation j/k/up/down | SATISFIED | BINDINGS + action_cursor_up/down verified |
| WKTR-CURSOR-02 | 260414-k2u-PLAN.md | Enter activates MR URL or IDE | SATISFIED | action_activate_row with both branches verified and tested |
| WKTR-CURSOR-03 | 260414-k2u-PLAN.md | Escape returns focus to project list | SATISFIED | action_focus_projects verified |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `worktree_pane.py` | 268 | "placeholder" in docstring | Info | Describes Loading... state per design (D-05) — not a stub |

No blockers or warnings found.

### Human Verification Required

#### 1. Footer hints visible when Worktrees pane is focused

**Test:** Launch `joy` in a project with active worktrees. Tab to the Worktrees pane.
**Expected:** Footer shows j / k / Enter / Esc binding hints.
**Why human:** Footer hint rendering is visual/runtime behavior — BINDINGS presence is verified programmatically but the footer display requires a running TUI.

#### 2. Cursor movement and GroupHeader skipping

**Test:** With Worktrees pane focused, press j and k repeatedly.
**Expected:** Cursor moves between worktree rows (highlighted in accent color). Repo name headers are never selected — cursor skips directly from the last worktree of one repo to the first of the next.
**Why human:** CSS highlight and row-skip behavior requires visual confirmation in a running TUI.

#### 3. Enter opens MR URL in browser

**Test:** Navigate to a worktree row that has an open MR. Press Enter.
**Expected:** The system default browser opens the MR URL (GitHub PR or GitLab MR page).
**Why human:** Requires a live worktree with an open MR — cannot fully replicate in unit tests without actual `gh`/`glab` CLI output.

#### 4. Enter opens worktree in IDE when no MR

**Test:** Navigate to a worktree row with no MR. Press Enter.
**Expected:** The worktree path opens in the IDE configured in `~/.joy/config.toml` (default: PyCharm).
**Why human:** Requires a live worktree without an MR and the configured IDE installed.

#### 5. Escape returns focus to project list

**Test:** While the Worktrees pane is focused, press Escape.
**Expected:** Focus moves to the project list pane on the left; Worktrees pane border reverts from accent to default color.
**Why human:** Focus transfer and border color change require visual inspection of the running TUI.

### Gaps Summary

No gaps. All 6 observable truths are verified by code inspection and passing tests. The 5 human verification items are runtime/visual behaviors that cannot be confirmed programmatically — they require manual smoke-testing with a live `joy` session.

---

_Verified: 2026-04-14T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
