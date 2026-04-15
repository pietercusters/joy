---
phase: 260415-gw0
verified: 2026-04-15T10:00:00Z
status: gaps_found
score: 6/7 must-haves verified
overrides_applied: 0
gaps:
  - truth: "Terminal pane e: Rename hint matches an actual binding"
    status: failed
    reason: "_PANE_HINTS['terminal-pane'] advertises 'e: Rename' but no Binding('e', 'rename_session', ...) exists in TerminalPane.BINDINGS. The action_rename_session method exists but is unreachable via keyboard."
    artifacts:
      - path: "src/joy/widgets/terminal_pane.py"
        issue: "TerminalPane.BINDINGS has no 'e' key binding; action_rename_session is an orphaned method"
      - path: "src/joy/app.py"
        issue: "_PANE_HINTS['terminal-pane'] = 'e: Rename  Enter: Focus' misleads user — e does nothing"
    missing:
      - "Add Binding('e', 'rename_session', 'Rename') to TerminalPane.BINDINGS"
---

# Quick Task 260415-gw0: Keyboard Shortcuts Verification Report

**Task Goal:** Rethink all keyboard shortcuts and add two rows of keyboard hints at the bottom
**Verified:** 2026-04-15
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Two-row HintBar widget exists, docked at bottom | VERIFIED | `src/joy/widgets/hint_bar.py`: Widget with `dock: bottom`, `height: 2`, renders `pane_hints\nglobal_hints` |
| 2 | Global shortcuts b/m/i/y/u/t/h/R are all bound and wired in JoyApp | VERIFIED | `app.py` lines 68-75: all 8 global bindings present; action methods (`action_open_branch`, etc.) implemented with `_open_first_of_kind` dispatch |
| 3 | Pane-specific hints update dynamically based on focused pane | VERIFIED | `on_descendant_focus` updates `HintBar.pane_hints` from `_PANE_HINTS` dict; worktrees pane correctly gets empty string |
| 4 | `n` is scoped to ProjectList only (not firing globally from TerminalPane/WorktreePane) | VERIFIED | No `n` binding in `JoyApp.BINDINGS`; `Binding("n", "new_project", "New", show=True)` in `ProjectList.BINDINGS` only; delegates to `self.app.action_new_project()` |
| 5 | `o` binding present in both WorktreePane and TerminalPane | VERIFIED | WorktreePane.BINDINGS line 255: `Binding("o", "activate_row", "Open", show=False)`; TerminalPane.BINDINGS line 177: `Binding("o", "focus_session", "Open", show=False)` |
| 6 | KIND_SHORTCUT dict and col-shortcut column exist in ObjectRow showing inline [key] hints | VERIFIED | `object_row.py` lines 12-20: `KIND_SHORTCUT` maps 7 kinds to b/m/i/y/u/t/h; CSS defines `col-shortcut`; `compose()` yields `Static(f"[{shortcut}]" ...)` |
| 7 | Terminal pane e: Rename hint matches an actual binding | FAILED | `_PANE_HINTS["terminal-pane"]` = `"e: Rename  Enter: Focus"` but TerminalPane.BINDINGS has no `e` binding — `action_rename_session` method exists but is unreachable via keyboard |

**Score:** 6/7 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/joy/widgets/hint_bar.py` | Two-row footer widget | VERIFIED | 35 lines; HintBar Widget with reactive pane_hints and hardcoded global_hints; render() outputs two-line string |
| `src/joy/app.py` | Global b/m/i/y/u/t/h/R bindings + HintBar wired | VERIFIED | All 8 global bindings in BINDINGS; `yield HintBar()` in compose(); `_PANE_HINTS` dict defined; `on_descendant_focus` updates pane hints |
| `src/joy/widgets/project_list.py` | `n` binding scoped here | VERIFIED | `Binding("n", "new_project", "New", show=True)` + `action_new_project` delegating to app |
| `src/joy/widgets/terminal_pane.py` | `o` binding present, no spurious `e: rename_session` binding | VERIFIED (partial) | `o` binding confirmed; `action_rename_session` method is orphaned — no `e` key binding, though `_PANE_HINTS` says otherwise |
| `src/joy/widgets/worktree_pane.py` | `o` binding + `[i]` hint on rows | VERIFIED | `o` binding present; `build_content()` appends `"  [i]"` in both default-branch (line 183) and non-default-branch (line 209) code paths |
| `src/joy/widgets/object_row.py` | KIND_SHORTCUT dict + col-shortcut column | VERIFIED | KIND_SHORTCUT dict maps 7 PresetKinds; `col-shortcut` CSS class; compose yields shortcut Static |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| JoyApp.on_descendant_focus | HintBar.pane_hints | `_PANE_HINTS` dict lookup | WIRED | Lines 455-457 in app.py update `HintBar.pane_hints` on focus change |
| JoyApp.BINDINGS b/m/i/y/u/t/h | `_open_first_of_kind(PresetKind.X)` | action methods | WIRED | All 7 action_open_* methods delegate to `_open_first_of_kind`; branch uses pbcopy, others use open_object |
| ProjectList n binding | JoyApp.action_new_project | `self.app.action_new_project()` | WIRED | project_list.py line 358 |
| WorktreeRow.build_content | `[i]` hint text | `t.append("  [i]", style="dim")` | WIRED | Lines 183 and 209 — both default and non-default branches |
| SessionRow._build_content | `[h]` hint text | `t.append("  [h]", style="dim")` | WIRED | Line 145, after cwd append |
| ObjectRow.compose | col-shortcut column | `KIND_SHORTCUT.get(self.item.kind)` | WIRED | Line 129 |

### Post-Checkpoint Bug Fix Verification

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| `n` NOT in JoyApp.BINDINGS | Absent | Absent — not found in lines 60-76 | PASS |
| `e: rename_session` NOT in TerminalPane.BINDINGS | Absent | Absent — TerminalPane.BINDINGS has 7 entries, none with key "e" | PASS |
| `o` binding in WorktreePane | Present | `Binding("o", "activate_row", "Open", show=False)` at line 255 | PASS |
| `o` binding in TerminalPane | Present | `Binding("o", "focus_session", "Open", show=False)` at line 177 | PASS |
| KIND_SHORTCUT dict in ObjectRow | Present | Lines 12-20: 7-entry dict | PASS |
| `col-shortcut` CSS column in ObjectRow | Present | Line 88 CSS; line 129 compose | PASS |
| WorktreeRow.build_content appends `[i]` | Present | Lines 183 and 209 | PASS |
| SessionRow._build_content appends `[h]` | Present | Line 145 | PASS |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/joy/app.py` | 28 | `_PANE_HINTS["terminal-pane"]` = `"e: Rename  Enter: Focus"` | Blocker | Advertises a keyboard shortcut (`e`) that is not bound in TerminalPane.BINDINGS — user sees hint but key does nothing |
| `src/joy/widgets/terminal_pane.py` | 370 | `action_rename_session` method exists with no binding | Warning | Dead code — reachable only if binding is added; method itself is fully implemented |

### Human Verification Required

None — all checks are code-level.

### Gaps Summary

One gap blocks full goal achievement: the terminal pane `e: Rename` hint is advertised in `_PANE_HINTS` and displayed in Row 1 of the HintBar when terminal pane is focused, but the actual `e` key binding is missing from `TerminalPane.BINDINGS`. The `action_rename_session` method is fully implemented and functional — only the `Binding("e", "rename_session", "Rename")` entry in `TerminalPane.BINDINGS` is missing. Fix: add that single binding line and the feature works end-to-end.

The CONTEXT.md explicitly specified "Terminal pane does get `e` for renaming a session" — this was planned scope that was incompletely implemented (SUMMARY incorrectly claimed no changes were needed for this item, conflating the absence of a _broken_ binding with the planned addition of a new one).

---

_Verified: 2026-04-15T10:00:00Z_
_Verifier: Claude (gsd-verifier)_
