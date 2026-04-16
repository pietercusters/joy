# Phase 17: Fix iTerm2 Integration Bugs - Context

**Gathered:** 2026-04-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix three specific bugs in the iTerm2 tab integration introduced by quick-260416-of2:

1. **No auto-sync** — remove all automatic tab creation. Tabs are only created when the user presses 'h' on a project with no linked tab.
2. **Tab-level close** — deleting or archiving a project closes the entire iTerm2 Tab (not individual sessions). The Terminal pane's per-session close operations (d/D bindings) remain unchanged.
3. **Test isolation** — all unit tests must never touch `~/.joy/`. An autouse fixture in `conftest.py` patches all store path constants globally.

**Relationship model (clarified):**
- Project ↔ iTerm2 Tab: one-to-one via `Project.iterm_tab_id`
- Tab → Sessions: one-to-many (user can spawn extra sessions inside a tab)
- Terminal pane still shows all active sessions; per-session close from the Terminal pane is unaffected by this phase

</domain>

<decisions>
## Implementation Decisions

### Bug 1: Remove auto-sync

- **D-01:** Remove the auto-create branch from `_set_terminal_sessions` in `app.py`. The stale-heal branch (clear `iterm_tab_id` when tab no longer in `live_tab_ids`) stays, but the `elif project.iterm_tab_id is None` branch that calls `_do_create_tab_for_project` is deleted.
- **D-02:** Remove the `_do_create_tab_for_project(project)` call from `action_new_project`. New project creation no longer auto-creates an iTerm2 tab.
- **D-03:** Modify `action_open_terminal` (h key): if `project.iterm_tab_id` is set and live → activate the tab. If `iterm_tab_id` is `None` (no tab linked) → call `_do_create_tab_for_project(project)` to create and link one. This is the ONLY trigger for tab creation.
- **D-04:** The `_tabs_creating` guard set stays — prevents duplicate create workers if the user hammers 'h' before the first worker completes.

### Bug 1: Stale-heal behavior after auto-sync removal

- **D-05:** When a tab_id is stale (not in `live_tab_ids`): clear `project.iterm_tab_id = None`, save to disk, AND emit a status bar notification: `"'{project.name}' tab closed — press h to relink"` (per `self.notify()`). No auto-recreate.
- **D-06:** Stale-heal still happens in `_set_terminal_sessions` on every refresh tick — just clearing, no creating.

### Bug 2: Tab-level close

- **D-07:** Add `close_tab(tab_id: str, force: bool = False) -> bool` to `terminal_sessions.py`. Implementation: iterate `app.terminal_windows` → `window.tabs`, find `tab.tab_id == tab_id`, call `tab.async_close(force=force)`. Returns `True` on success (or if tab already gone), `False` on exception. Same lazy-import and silent-fail contract as all other functions in that module.
- **D-08:** Add `_close_tab_bg(tab_id: str)` worker to `JoyApp` (mirrors `_close_sessions_bg` but operates on a whole tab). `@work(thread=True, exit_on_error=False)`. Calls `close_tab(tab_id, force=False)`.
- **D-09:** On project **delete**: if `project.iterm_tab_id` is set, call `self._close_tab_bg(project.iterm_tab_id)` before (or alongside) `_save_projects_bg`. No user choice — tab always closes.
- **D-10:** On project **archive**: always close the tab. Simplify `action_archive_project` in `project_list.py` to use `ConfirmationModal` instead of `ArchiveModal`. Prompt: `"Archive project '{name}'? This will archive it and close its iTerm2 tab."`. Remove `ArchiveModal`, `ArchiveChoice`, and the `ARCHIVE_WITH_CLOSE` / `ARCHIVE_ONLY` branching from `project_list.py`.
- **D-11:** `_close_sessions_bg` in `app.py` stays as-is — it is still used by the Terminal pane's per-session close flow. Not touched in this phase.
- **D-12:** If `project.iterm_tab_id` is `None` at delete/archive time, skip the tab-close call silently (no error, no notification).

### Bug 3: Test isolation

- **D-13:** Add an `autouse=True`, `scope="session"` fixture in `tests/conftest.py` using `tmp_path_factory`. It patches `joy.store.PROJECTS_PATH`, `joy.store.CONFIG_PATH`, `joy.store.REPOS_PATH`, and `joy.store.ARCHIVE_PATH` to paths inside a session-scoped temporary directory. Uses `unittest.mock.patch` (or `monkeypatch` via `tmp_path_factory`). All tests automatically get isolated paths — no individual test changes needed.
- **D-14:** The fixture also ensures `joy.store.JOY_DIR` is patched so any code that reads that constant directly (e.g., `mkdir(parents=True)` calls) also uses the tmp directory.
- **D-15:** Existing `test_store.py` tests that already pass explicit `tmp_path` paths to `save_projects(path=...)` etc. stay unchanged. The new autouse fixture is additive — it prevents accidental real-path writes from any test that doesn't override the path explicitly.

### Claude's Discretion

- Whether to use `monkeypatch` (via `monkeypatch` fixture adapted for session scope using `pytest.MonkeyPatch()`) or `unittest.mock.patch` as context manager for the conftest fixture.
- Exact wording of stale-heal notification beyond the format in D-05.
- Whether to delete `archive_modal.py` entirely or keep it as an empty stub. Deleting is cleaner if no other code imports it.
- Function vs session scope for the test fixture — if inter-test state bleed is observed, downgrade to `scope="function"`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Core files being modified
- `src/joy/app.py` — `_set_terminal_sessions`, `action_new_project`, `action_open_terminal`, `_close_sessions_bg`, `_do_create_tab_for_project`, `_tabs_creating`
- `src/joy/terminal_sessions.py` — `create_tab`, `close_session`, `activate_session`; add `close_tab`
- `src/joy/widgets/project_list.py` — `action_delete_project`, `action_archive_project`
- `tests/conftest.py` — add autouse store-path fixture

### Reference for iTerm2 integration patterns
- `.planning/phases/12-iterm2-integration-terminal-pane/12-CONTEXT.md` — D-02 threading model, D-03 silent-fail contract, D-12 activate pattern
- `.planning/phases/17-fix-iterm2-integration-bugs-from-quick-260416-of2-remove-aut/17-CONTEXT.md` (this file)

### Screens being removed/replaced
- `src/joy/screens/archive_modal.py` — `ArchiveModal` and `ArchiveChoice` to be removed; replaced by `ConfirmationModal`
- `src/joy/screens/__init__.py` — remove `ArchiveModal` / `ArchiveChoice` export if present

### Test infrastructure
- `tests/conftest.py` — existing fixtures (do not break); add store-path autouse fixture
- `src/joy/store.py` — `JOY_DIR`, `PROJECTS_PATH`, `CONFIG_PATH`, `REPOS_PATH`, `ARCHIVE_PATH` constants (patch targets)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ConfirmationModal` in `src/joy/screens/__init__.py` — already used by delete project; reuse for archive simplification (D-10)
- `_close_sessions_bg(sessions)` in `app.py:889` — existing background worker pattern; mirror for `_close_tab_bg`
- `_do_create_tab_for_project(project)` in `app.py:671` — existing create worker; move trigger from refresh to h-key only
- `_tabs_creating: set[str]` in `app.py:98` — in-flight guard; keep for h-key debounce

### Established Patterns
- All iTerm2 functions in `terminal_sessions.py` use the same pattern: lazy import, `Connection().run_until_complete(...)`, try/except returns None/False
- `@work(thread=True, exit_on_error=False)` + `call_from_thread` for all background workers
- Notification: `self.notify(message, markup=False)` for status bar messages (no severity = info)
- `unittest.mock.patch` already used in `tests/test_store.py` for path patching

### Integration Points
- `_set_terminal_sessions` (app.py) is the only place stale-heal + auto-create currently live → remove only the auto-create branch
- `action_archive_project` in `project_list.py:550` calls `_close_sessions_bg` conditionally → replace with unconditional `_close_tab_bg`
- `action_delete_project` in `project_list.py:471` has no tab cleanup → add `_close_tab_bg` call

</code_context>

<specifics>
## Specific Ideas

- The iTerm2 `Tab` object has `async_close(force=False)` — this closes all sessions inside the tab at once. Use this in `close_tab()`.
- `_close_tab_bg` should mirror `_close_sessions_bg` exactly but accept a `tab_id: str` instead of a sessions list.
- The `_tabs_creating` guard in D-04 means: if the user presses 'h' and a create worker is already running for this project, `_do_create_tab_for_project` will not start a second worker (the guard check stays in `_set_terminal_sessions` for the stale-heal path, AND we add the same guard check in `action_open_terminal` before calling `_do_create_tab_for_project`).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 17-fix-iterm2-integration-bugs-from-quick-260416-of2-remove-aut*
*Context gathered: 2026-04-16*
