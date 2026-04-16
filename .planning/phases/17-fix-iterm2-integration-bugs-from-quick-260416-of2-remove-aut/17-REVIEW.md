---
phase: 17-fix-iterm2-integration-bugs-from-quick-260416-of2-remove-aut
reviewed: 2026-04-16T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - src/joy/terminal_sessions.py
  - tests/conftest.py
  - src/joy/app.py
  - src/joy/widgets/project_list.py
  - src/joy/screens/__init__.py
  - tests/test_terminal_sessions.py
findings:
  critical: 0
  warning: 3
  info: 4
  total: 7
status: issues_found
---

# Phase 17: Code Review Report

**Reviewed:** 2026-04-16T00:00:00Z
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Six files were reviewed covering the iTerm2 integration module, the main app entry point, the project list widget, the screens re-export, a conftest fixture, and the terminal session unit tests.

The code is well-structured. The iTerm2 API wrappers use the correct `Connection().run_until_complete()` pattern with lazy imports and broad exception handling. The stale-tab healing logic in `_set_terminal_sessions` is sound. The project list widget's repo-grouping and cursor management are clean.

Three warnings were found: the `_tabs_creating` in-flight guard has a failure-path leak that permanently blocks retry for a project if `create_tab` raises unexpectedly, the `_do_activate_tab` worker uses an inconsistent `call_from_thread(self.notify, ...)` pattern where all other workers call `self.notify` directly, and `pick_best_mr` is typed to accept `object` for `rel_index` but calls methods on it unconditionally with type-ignore comments suppressing the checker. Four informational items cover a dead `create_session` function, a dead module-level `subprocess` import in `app.py`, the `_SHELL_PROCESSES` constant lacking tests for `"sh"` and `"dash"` entries, and an action-name semantic inversion in the sync toggle bindings.

## Warnings

### WR-01: `_tabs_creating` guard never cleared if `create_tab` raises unexpectedly before `call_from_thread`

**File:** `src/joy/app.py:664-678`
**Issue:** `_do_create_tab_for_project` is decorated `@work(thread=True, exit_on_error=False)`. Inside the worker, `create_tab(project_name)` is called, followed by `self.app.call_from_thread(_apply)`. The `_apply` callback always calls `self._tabs_creating.discard(project_name)`. However, `create_tab` itself wraps everything in a `try/except Exception: pass` and always returns, so an unhandled raise before `call_from_thread` is theoretically impossible in this specific chain. The more realistic gap is that `_apply` correctly discards the guard on both the `tab_id` and `None` (failure) paths — but the code structure makes this non-obvious and fragile: any future code added between `tab_id = create_tab(...)` and `self.app.call_from_thread(_apply)` that could raise would silently leave the project stuck in `_tabs_creating` until app restart, silently ignoring all subsequent `h` keypresses.

**Fix:** Wrap the body in a try/finally to guarantee `_apply` always schedules:

```python
@work(thread=True, exit_on_error=False)
def _do_create_tab_for_project(self, project: Project) -> None:
    from joy.terminal_sessions import create_tab  # noqa: PLC0415
    project_name = project.name
    tab_id: str | None = None
    try:
        tab_id = create_tab(project_name)
    finally:
        def _apply(tab_id: str | None = tab_id) -> None:
            self._tabs_creating.discard(project_name)
            if tab_id:
                project.iterm_tab_id = tab_id
                self._save_projects_bg()
                self._load_terminal()
        self.app.call_from_thread(_apply)
```

---

### WR-02: `_do_activate_tab` dispatches `self.notify` via `call_from_thread` — inconsistent with all other workers

**File:** `src/joy/app.py:690`
**Issue:** Every other `@work(thread=True)` method in `JoyApp` that needs to emit a notification calls `self.notify(...)` directly (Textual makes `notify` thread-safe). `_do_activate_tab` alone uses the redundant double-dispatch pattern `self.app.call_from_thread(self.notify, ...)`. This is not a bug (the call is safe), but it is misleading: readers seeing `call_from_thread(self.notify, ...)` conclude that `self.notify` is not thread-safe (otherwise why wrap it?), which then creates pressure to add the same wrapper elsewhere. The inconsistency will grow over time.

**Fix:**
```python
# Replace line 690:
self.app.call_from_thread(self.notify, "Tab session not found", severity="warning", markup=False)
# With:
self.notify("Tab session not found", severity="warning", markup=False)
```

---

### WR-03: `pick_best_mr` calls methods on `rel_index: object` without None guard; type-ignore comments suppress the checker

**File:** `src/joy/widgets/project_list.py:237`
**Issue:** The function signature is `def pick_best_mr(project, mr_data, rel_index: object)`. At line 237, `rel_index.worktrees_for(project)` is called with `# type: ignore[union-attr]` suppressing the type checker's complaint. The callers always pass a non-None `RelationshipIndex`, so this is not a runtime bug today. However, the `# type: ignore` comments disable the static check that would catch a future caller passing `None`. If `pick_best_mr` is called with `rel_index=None` (which the signature permits), the code raises `AttributeError` at runtime on line 237.

**Fix:** Tighten the type signature and add a guard:

```python
from joy.resolver import RelationshipIndex  # add to top-level imports

def pick_best_mr(
    project: "Project",
    mr_data: dict,
    rel_index: "RelationshipIndex | None",
) -> "MRInfo | None":
    if mr_data and project.repo is not None and rel_index is not None:
        for wt in rel_index.worktrees_for(project):
            ...
```

Remove both `# type: ignore[union-attr]` comments at lines 237 and 252 once the guard is in place.

---

## Info

### IN-01: `create_session` is dead code — superseded by `create_tab`, never called

**File:** `src/joy/terminal_sessions.py:109-137`
**Issue:** `create_session` (returns `session_id`) has no callers anywhere in the codebase. `create_tab` (returns `tab_id`) replaced it. The dead function adds maintenance surface and reader confusion since both functions have near-identical bodies.

**Fix:** Remove `create_session`, or if kept for future use, add a `# DEPRECATED: use create_tab instead` comment and export it explicitly if it is part of the public API.

---

### IN-02: Module-level `import subprocess` in `app.py` is dead — the only user re-imports it locally

**File:** `src/joy/app.py:4`
**Issue:** `import subprocess` at the top of `app.py` is never used at module scope. `_copy_branch` (line 751) does `import subprocess` locally with a `# noqa: PLC0415` comment, consistent with the lazy-import convention used throughout the file. The module-level import is unreachable dead code.

**Fix:** Remove line 4 (`import subprocess`) from `app.py`. The local import in `_copy_branch` is sufficient.

---

### IN-03: `_SHELL_PROCESSES` test coverage missing `"sh"` and `"dash"`

**File:** `tests/test_terminal_sessions.py:244-258`
**Issue:** `TestShellProcesses` asserts membership of `"zsh"`, `"bash"`, and `"fish"` but not `"sh"` or `"dash"`, which were added to the frozenset in a later phase. If either of these is removed from the implementation, no test catches the regression.

**Fix:**
```python
def test_shell_processes_contains_sh(self):
    assert "sh" in _SHELL_PROCESSES

def test_shell_processes_contains_dash(self):
    assert "dash" in _SHELL_PROCESSES
```

---

### IN-04: Sync binding action names have inverted semantics (`disable_sync` re-enables sync, `toggle_sync` disables it)

**File:** `src/joy/app.py:67-68`, `716-724`
**Issue:** `action_toggle_sync` (line 716) sets `self._sync_enabled = False` — it turns sync OFF. `action_disable_sync` (line 722) sets `self._sync_enabled = True` — it turns sync ON. The action names are the opposite of what they do. The `check_action` logic and binding labels are behaviorally correct, but a reader of `action_disable_sync` will expect it to disable sync, not enable it. This will cause confusion when adding future sync-related features.

**Fix:** Rename `action_disable_sync` → `action_enable_sync` (and `"disable_sync"` → `"enable_sync"` in the `Binding` definition, `check_action`, and `action_disable_sync` method name). Low-risk internal rename.

---

_Reviewed: 2026-04-16T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
