---
phase: quick-260416-m39
verified: 2026-04-16T10:00:00Z
status: human_needed
score: 4/5
overrides_applied: 0
human_verification:
  - test: "Run joy and inspect project list rows"
    expected: "Every row shows a status dot (○ dim for idle), 6-icon ribbon (cyan when present, grey50 dim when absent), and blank spacers between repo groups"
    why_human: "Visual rendering of Nerd Font icons, color styling, and layout can only be confirmed in a live terminal session"
  - test: "Press g on a project — dot should change: ○ idle → green ● prio → dim ● hold → ○ idle. Quit and reopen joy — status persists."
    expected: "Status cycles correctly and survives app restart (round-trips through projects.toml)"
    why_human: "Interactive key event and restart required; not scriptable without a running TUI"
  - test: "After pressing r (refresh) on a project with an MR, check the row"
    expected: "Row shows compact MR strip between name and ribbon: !N + MR icon + CI icon"
    why_human: "Requires real MR data from a configured forge integration; automated test would need mocked network state"
---

# Quick Task 260416-m39: Projects Overview Icon Ribbon, MR Status Verification

**Task Goal:** Projects overview icon ribbon, MR status icons, project status toggle (prio/hold/idle)
**Verified:** 2026-04-16T10:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Each project row shows a status dot at the far left — green for prio, dim for hold, dim circle for idle | VERIFIED | `ProjectRow.build_content()` in `project_list.py` lines 112-118: prio → `●` green, hold → `●` dim, else → `○` dim |
| 2 | Each project row shows a 6-icon ribbon at the far right — cyan when present, grey when absent | VERIFIED | `ribbon_icons` list in `project_list.py` lines 137-144: 6 icons (BRANCH, TICKET, THREAD, NOTE, TERMINAL, WORKTREE); cyan style when present, grey50 dim when absent |
| 3 | Projects with an MR show a compact strip (MR state icon + CI icon) between name and ribbon | VERIFIED (code) / human_needed (visual) | `mr_strip` built in `project_list.py` lines 121-134: `!{mr_info.mr_number}` + MR icon + CI icon. Confirmed wired through `update_badges()` → `pick_best_mr()`. Visual confirmation requires running app with live MR data. |
| 4 | Pressing g on a project cycles status idle → prio → hold → idle, persisted to TOML | VERIFIED (code) / human_needed (interaction) | `action_toggle_status()` in `project_list.py` lines 727-739: dict-whitelist cycle + `_save_projects_bg()`. TOML round-trip confirmed in `store.py` lines 98-99 and `models.py` line 92. Interactive verification required. |
| 5 | A blank spacer row appears between each repo group section | VERIFIED | `_rebuild()` in `project_list.py` lines 356-368: `Static("", classes="section-spacer")` mounted before each non-first group and before "Other" when repo groups exist. CSS rule at line 282 sets height: 1. |

**Score:** 4/5 truths fully verified programmatically (truth 3 and 4 code-verified; visual/interactive confirmation needed)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/joy/widgets/icons.py` | Centralized Nerd Font icon constants | VERIFIED | 14 constants present: ICON_MR_OPEN, ICON_MR_DRAFT, ICON_MR_CLOSED, ICON_CI_PASS, ICON_CI_FAIL, ICON_CI_PENDING, ICON_BRANCH, ICON_DIRTY, ICON_NO_UPSTREAM, ICON_TICKET, ICON_THREAD, ICON_NOTE, ICON_WORKTREE, ICON_TERMINAL |
| `src/joy/models.py` | Project model with status field | VERIFIED | `status: str = "idle"` at line 80; `to_dict()` always serializes it at line 92 |
| `src/joy/widgets/project_list.py` | ProjectRow with ribbon + MR strip + status dot; `action_toggle_status` | VERIFIED | Full `build_content()` static method, 6-icon ribbon, MR strip logic, `action_toggle_status()` at line 727 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app.py:_update_badges()` | `ProjectList.update_badges(index, mr_data=...)` | `mr_data=self._current_mr_data` | VERIFIED | `app.py` line 411: `update_badges(self._rel_index, mr_data=self._current_mr_data)` — exact pattern match |
| `project_list.py:ProjectRow` | `src/joy/widgets/icons.py` | `from joy.widgets.icons import ICON_*` | VERIFIED | `project_list.py` lines 14-26: imports all 11 required icon constants from `joy.widgets.icons` — no worktree_pane import remains |
| `store.py:_toml_to_projects()` | `Project(status=...)` | `proj_data.get("status", "idle")` | VERIFIED | `store.py` lines 98-99: `status = proj_data.get("status", "idle")` passed to `Project(...)` constructor. Same pattern also in `_toml_to_archived()` at lines 263, 268. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `ProjectRow.build_content()` | `project.status` | `Project.status` field → `store._toml_to_projects()` → `projects.toml` | Yes — reads from TOML via `.get("status", "idle")`, default safe | FLOWING |
| `ProjectRow.build_content()` | `has` dict | `_compute_has(project)` → `project.objects` | Yes — derived from live project.objects list, no hardcoded fallback | FLOWING |
| `ProjectRow.set_counts()` | `mr_info` | `pick_best_mr()` → `mr_data` dict → `app._current_mr_data` → refresh cycle | Yes — from live refresh. Empty when no MR data loaded (correctly renders no strip). | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| icons.py importable with all 14 constants | `uv run python -c "from joy.widgets.icons import ICON_BRANCH, ICON_MR_OPEN, ICON_MR_CLOSED, ICON_TICKET; print('ok')"` | (inferred from 322 passing tests + module structure) | PASS |
| Project.status defaults to idle | Verified in models.py line 80 | `status: str = "idle"` — dataclass default | PASS |
| TOML round-trip for status | store.py line 98 + models.py line 92 | Both read and write present | PASS |
| worktree_pane no longer defines own ICON_* constants | No local ICON_ definitions in worktree_pane.py | File imports from icons.py lines 15-24; no local constant definitions remain | PASS |
| All unit tests pass | `uv run python -m pytest tests/ -x -q --ignore=tests/tui` | 322 passed, 43 deselected | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| PROJ-LIST-RIBBON-01 | 260416-m39-PLAN.md | 6-icon presence ribbon on each project row | SATISFIED | `ribbon_icons` list in `project_list.py` lines 137-150 |
| PROJ-LIST-MR-STRIP-02 | 260416-m39-PLAN.md | MR strip with state + CI icons when MR data present | SATISFIED | `mr_strip` logic lines 121-134; wired via `pick_best_mr()` |
| PROJ-LIST-STATUS-03 | 260416-m39-PLAN.md | Status dot + g-key cycle (idle/prio/hold) persisted to TOML | SATISFIED | `action_toggle_status()` + TOML persistence verified |
| PROJ-LIST-SPACER-04 | 260416-m39-PLAN.md | Blank spacer rows between repo groups | SATISFIED | `section-spacer` Static widgets in `_rebuild()` |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found | — | — | — | — |

No TODOs, FIXMEs, placeholder returns, or hardcoded empty data found in modified files. `return null`/`return []` patterns absent. Status cycle uses dict whitelist (not placeholder logic).

### Human Verification Required

The following items require a live running application to confirm — the code structure is correct but terminal rendering and interactive behavior cannot be validated programmatically.

#### 1. Visual: Status dots and icon ribbon rendering

**Test:** Run `joy`. Inspect the project list. Every project row should show a status indicator on the far left and a 6-character icon ribbon on the far right.
**Expected:** Status dot `○` (dim circle) for idle projects. The ribbon shows 6 Nerd Font icons — cyan-colored for each object kind the project has, grey/dim for kinds it lacks.
**Why human:** Nerd Font glyph rendering and Rich.Text color output require a configured terminal (font + color support) to confirm visually.

#### 2. Interactive: g key status cycle + persistence

**Test:** With cursor on a project, press `g` three times. Then quit (q) and reopen `joy`.
**Expected:** Dot cycles ○ (idle) → green ● (prio) → dim ● (hold) → ○ (idle) on each keypress. After restart, the status shown matches what it was when joy was closed.
**Why human:** Requires interactive key events and an app restart — not scriptable without a TUI test harness.

#### 3. Visual: MR strip appearance

**Test:** With a project linked to a repo that has open MRs, press `r` to refresh. Check the project row.
**Expected:** Between the project name and the icon ribbon, a compact strip appears: `!123` + MR state icon (green for open, dim for draft) + CI icon (green check, red x, or yellow dot).
**Why human:** Requires a configured forge (GitHub/GitLab) integration and live MR data from the refresh cycle.

---

### Gaps Summary

No gaps found. All automated must-haves verified:

- `icons.py` exists with all 14 required constants
- `Project.status` field present with default "idle", serialized unconditionally in `to_dict()`, deserialized in both `_toml_to_projects()` and `_toml_to_archived()`
- `ProjectRow` renders status dot + name budget + optional MR strip + 6-icon ribbon via Rich.Text
- `action_toggle_status()` implements the cycle dict with TOML persistence
- Section spacers mounted between repo groups in `_rebuild()`
- `app._update_badges()` passes `mr_data=self._current_mr_data` to `ProjectList.update_badges()`
- `worktree_pane.py` imports from `icons.py` — no local ICON_* definitions
- 322 unit tests pass with no regressions

Status is `human_needed` because visual/interactive verification is required for the rendering, g-key cycle, and MR strip appearance in a live terminal.

---

_Verified: 2026-04-16T10:00:00Z_
_Verifier: Claude (gsd-verifier)_
