---
phase: quick-260415-qqx
verified: 2026-04-15T10:00:00Z
status: gaps_found
score: 11/13 must-haves verified
overrides_applied: 0
gaps:
  - truth: "All references to 'agents'/'AGENTS' in code are renamed to 'terminals'/'TERMINALS'"
    status: failed
    reason: "src/joy/widgets/project_list.py line 454 calls index.agents_for(row.project) which does not exist in the renamed resolver. The method is now terminals_for(). This will raise AttributeError at runtime whenever _update_badges() is called after a refresh cycle."
    artifacts:
      - path: "src/joy/widgets/project_list.py"
        issue: "Line 454: index.agents_for(row.project) — agents_for does not exist on RelationshipIndex; should be terminals_for"
    missing:
      - "Change line 454 in src/joy/widgets/project_list.py from index.agents_for(row.project) to index.terminals_for(row.project)"
  - truth: "All tests pass with the renamed enums and new functionality"
    status: partial
    reason: "uv run pytest passes (314 tests), but the agents_for bug is not caught by any test because update_badges() is not exercised with a real RelationshipIndex in the test suite. The test suite passes but does not validate that badges work at runtime."
    artifacts:
      - path: "src/joy/widgets/project_list.py"
        issue: "update_badges calls agents_for which will AttributeError at runtime — not covered by tests"
    missing:
      - "Fix the agents_for call (see gap above) — test suite will then validate badges correctly"
---

# Quick Task: Build Full iTerm2 Terminal Session Control — Verification Report

**Task Goal:** Build full iTerm2 terminal session control in joy TUI — rename Agent/Terminal everywhere, add n/e/d/D key bindings in TerminalPane, auto-create session on project terminal add, auto-remove terminal object when session disappears, project-link flag in Terminals overview.
**Verified:** 2026-04-15T10:00:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | All references to 'agents'/'AGENTS' renamed to 'terminals'/'TERMINALS' | FAILED | `project_list.py:454` calls `index.agents_for(row.project)` — method does not exist; will AttributeError at runtime |
| 2 | User can press n in TerminalPane to create a new named iTerm2 session | VERIFIED | `TerminalPane.BINDINGS` includes `Binding("n", "action_new_session")`, `action_new_session` pushes NameInputModal and calls `_do_create_session` which calls `create_session()` |
| 3 | User can press e in TerminalPane to rename the highlighted session | VERIFIED | `Binding("e", "action_rename_session")` present; handler pushes NameInputModal with initial value and calls `rename_session()` |
| 4 | User can press d in TerminalPane to close a session with confirmation | VERIFIED | `Binding("d", "action_close_session")` present; pushes ConfirmationModal, calls `close_session(session_id, force=False)` |
| 5 | User can press D in TerminalPane to force-close a session with confirmation | VERIFIED | `Binding("D", "action_force_close_session")` present; pushes ConfirmationModal with force_close wording, calls `close_session(force=True)` |
| 6 | Adding a Terminal object to a project auto-creates an iTerm2 session | VERIFIED | `app.py _start_add_object_loop` checks `if preset == PresetKind.TERMINALS` and calls `_auto_create_terminal_session(value)` which calls `create_session(name)` in a background thread |
| 7 | Terminal objects are auto-removed from projects when their session disappears | VERIFIED | `_propagate_terminal_auto_remove()` in app.py scans projects, removes TERMINALS objects whose value is not in active session names, saves, and notifies |
| 8 | Linked sessions show a project-link icon in the Terminals overview | VERIFIED | `SessionRow._build_content()` appends `ICON_LINK` (nf-fa-link) in cyan when `is_linked=True`; `set_linked_names()` on TerminalPane updates rows; `_update_terminal_link_status()` in app.py propagates linked names from RelationshipIndex |
| 9 | Opening a Terminal object uses the Python API instead of AppleScript | VERIFIED | `operations.py _open_iterm()` uses `iterm2.async_get_app` + `Connection().run_until_complete()` — no osascript anywhere |
| 10 | Old TOML files with 'agents' kind are transparently read as 'terminals' | VERIFIED | `store.py _toml_to_projects` line 53: `if raw_kind == "agents": raw_kind = "terminals"` |
| 11 | ConfirmationModal accepts a custom hint string | VERIFIED | `ConfirmationModal.__init__` accepts `hint: str = "Enter to delete, Escape to cancel"` and renders it via `Static(self._hint)` |
| 12 | The stale field and --stale CSS are fully removed | VERIFIED | No `stale` field in `ObjectItem`, no `--stale` CSS class anywhere in source |
| 13 | All tests pass with the renamed enums and new functionality | PARTIAL | `uv run pytest` passes 314 tests, but `agents_for` bug in project_list.py is not exercised by any test — the badge-update path is untested |

**Score:** 11/13 truths verified (10 VERIFIED, 1 PARTIAL counted as failed, 1 FAILED)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/joy/models.py` | PresetKind.TERMINALS enum, stale field removed from ObjectItem | VERIFIED | TERMINALS = "terminals" present in PresetKind; ObjectItem has no stale field |
| `src/joy/terminal_sessions.py` | create_session(), rename_session(), close_session() functions | VERIFIED | All three functions present and substantive — use iterm2 Python API |
| `src/joy/operations.py` | Python API based _open_iterm() replacing AppleScript | VERIFIED | _open_iterm uses iterm2.async_get_app, not osascript |
| `src/joy/widgets/terminal_pane.py` | n/e/d/D bindings, linked_names flag display in SessionRow | VERIFIED | All 4 bindings present; ICON_LINK displayed when is_linked=True |
| `src/joy/app.py` | Auto-create hook, auto-remove logic, updated sync/propagation | VERIFIED | _auto_create_terminal_session + _propagate_terminal_auto_remove both implemented |
| `src/joy/resolver.py` | Renamed methods: terminals_for, project_for_terminal | VERIFIED | Both methods exist on RelationshipIndex |
| `src/joy/screens/confirmation.py` | Parameterized hint text | VERIFIED | hint parameter with default, rendered in compose() |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `terminal_pane.py` | `terminal_sessions.py` | n/e/d/D actions call create/rename/close_session | WIRED | `_do_create_session` imports `joy.terminal_sessions` and calls `_ts.create_session`; likewise for rename and close |
| `app.py` | `terminal_sessions.py` | `_start_add_object_loop` auto-create hook | WIRED | `_auto_create_terminal_session` imports `create_session` from `joy.terminal_sessions` |
| `app.py` | `resolver.py` | terminals_for/project_for_terminal calls | WIRED | `_sync_from_project` calls `self._rel_index.terminals_for(project)`; `_sync_from_session` calls `project_for_terminal` |
| `store.py` | `models.py` | backward compat alias agents->terminals in _toml_to_projects | WIRED | Line 53-54: `if raw_kind == "agents": raw_kind = "terminals"` then `PresetKind(raw_kind)` |
| `project_list.py` | `resolver.py` | update_badges calls agent counts | BROKEN | Line 454 calls `index.agents_for(row.project)` — `agents_for` does not exist; correct method is `terminals_for` |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/joy/widgets/project_list.py` | 454 | `index.agents_for(row.project)` — stale method name from before rename | Blocker | AttributeError at runtime when badges refresh after any worktree/terminal load cycle |

### Gaps Summary

One blocker found: `project_list.py` line 454 calls `index.agents_for(row.project)`. The `agents_for` method was removed from `RelationshipIndex` as part of the agent→terminal rename — the current method is `terminals_for`. This line escaped the rename pass and will raise `AttributeError: 'RelationshipIndex' object has no attribute 'agents_for'` at runtime every time `_update_badges()` runs (which happens after every refresh cycle). All 314 tests pass because the test for `update_badges` uses a mock index object that doesn't check method names.

Fix: change line 454 in `src/joy/widgets/project_list.py` from `agent_count = len(index.agents_for(row.project))` to `agent_count = len(index.terminals_for(row.project))`.

---

_Verified: 2026-04-15T10:00:00Z_
_Verifier: Claude (gsd-verifier)_
