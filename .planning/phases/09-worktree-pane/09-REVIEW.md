---
phase: 09-worktree-pane
reviewed: 2026-04-13T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - tests/test_worktree_pane.py
  - src/joy/widgets/worktree_pane.py
  - src/joy/app.py
  - tests/test_pane_layout.py
findings:
  critical: 0
  warning: 3
  info: 4
  total: 7
status: issues_found
---

# Phase 09: Code Review Report

**Reviewed:** 2026-04-13T00:00:00Z
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

This phase implements the worktree pane (bottom-right quadrant) with grouped display, status
indicators (dirty / no-upstream), path abbreviation, and empty-state messaging. The implementation
is coherent: `WorktreePane`, `WorktreeRow`, `GroupHeader`, `abbreviate_home`, and `middle_truncate`
are all present and structured correctly. The test suite is comprehensive and aligns well with the
implementation contracts.

Three warnings were found, none of which are crash-level bugs but each can produce silent wrong
behaviour:

1. `abbreviate_home` has an edge-case failure when the home directory path ends with a separator
   or the match is a false prefix.
2. `_load_worktrees` in `app.py` accesses `self._config` from a background thread without any
   synchronisation — a data-race on the config object.
3. `set_worktrees` uses `scroll.remove_children()` which is synchronous; re-mounting immediately
   inside the same method can cause a subtle double-render flicker and, if the Textual event loop
   is mid-cycle, may mount children into a partially-detached scroll container.

Four informational items are also noted (unused import, magic numbers, comment typo, test
reliability).

## Warnings

### WR-01: `abbreviate_home` — false-prefix match on paths that share a prefix with `$HOME`

**File:** `src/joy/widgets/worktree_pane.py:37`
**Issue:** The check `path_str.startswith(home)` can match paths that are *siblings* of the home
directory rather than children of it. For example, if `HOME=/Users/pieter` the path
`/Users/pietersen/Github/joy` starts with `/Users/pieter` and would be incorrectly abbreviated to
`~sen/Github/joy`. The bug does not crash but silently corrupts display output.

**Fix:**
```python
def abbreviate_home(path_str: str) -> str:
    home = str(Path.home())
    # Ensure we match only actual children/exact home, not sibling paths
    # that share a common prefix (e.g. /Users/pietersen when home=/Users/pieter)
    if path_str == home:
        return "~"
    if path_str.startswith(home + "/"):
        return "~" + path_str[len(home):]
    return path_str
```

The existing test `test_path_abbreviation` does not exercise this edge case and would miss the
regression.

---

### WR-02: Data race — `self._config` read in background thread without synchronisation

**File:** `src/joy/app.py:99`
**Issue:** `_load_worktrees` is decorated `@work(thread=True)` and reads `self._config.branch_filter`
directly from the worker thread. `self._config` is also written from the main thread by
`action_settings` → `_config = config` and by `_set_projects` → `self._config = config` (line 86).
There is no lock or copy around these accesses. In CPython the GIL reduces (but does not eliminate)
the risk of torn reads on simple attribute access; however a list assignment in the middle of a
`join()` in `list()` call can still produce a partial list. More critically, the reference
`self._config` itself could change between `_load_worktrees` reading the attribute and reading
`.branch_filter` on it.

**Fix:** Capture a local snapshot of `branch_filter` on the main thread before spawning the worker,
or pass the config value as a parameter:

```python
def _set_projects(self, projects: list[Project], config: Config | None = None) -> None:
    self._projects = projects
    if config is not None:
        self._config = config
    self.query_one(ProjectList).set_projects(projects)
    if projects:
        self.query_one(ProjectList).select_first()
    # Snapshot branch_filter before entering the thread
    self._load_worktrees(list(self._config.branch_filter))

@work(thread=True)
def _load_worktrees(self, branch_filter: list[str]) -> None:
    from joy.store import load_repos
    from joy.worktrees import discover_worktrees

    repos = load_repos()
    worktrees = discover_worktrees(repos, branch_filter)
    repo_count = len(repos)
    branch_filter_str = ", ".join(branch_filter) if branch_filter else ""
    self.app.call_from_thread(self._set_worktrees, worktrees, repo_count, branch_filter_str)
```

---

### WR-03: `set_worktrees` — synchronous `remove_children()` followed by immediate `mount()` calls

**File:** `src/joy/widgets/worktree_pane.py:222–258`
**Issue:** `scroll.remove_children()` schedules child removal (Textual processes DOM mutations
asynchronously), but the subsequent `scroll.mount(...)` calls in the same synchronous method
execute against the not-yet-cleared container. In practice this means that on the *second* call to
`set_worktrees` (the idempotency test exercises this), new rows are mounted before the old ones are
fully removed, causing a brief doubling of content. The test `test_set_worktrees_idempotent`
re-measures only after `pilot.pause(0.1)`, which hides the timing issue from the test but not from
a user who resizes the pane quickly.

**Fix:** Use Textual's `compose` / `refresh` pattern, or guard with `call_after_refresh`:

```python
def set_worktrees(self, worktrees, *, repo_count=0, branch_filter="") -> None:
    scroll = self.query_one("#worktree-scroll", _WorktreeScroll)
    # remove_children() is async; mount inside call_after_refresh to ensure
    # removal is committed before new children are added.
    def _rebuild():
        scroll.remove_children()
        self._loaded = True
        if not worktrees:
            ...  # mount empty-state
            return
        ...  # mount grouped rows

    scroll.call_after_refresh(_rebuild)
```

Alternatively, since the `_loaded` flag is also set inside `set_worktrees`, it too may be set
before removal completes if you keep the current structure — move `self._loaded = True` outside the
async boundary or accept the minor cosmetic risk.

---

## Info

### IN-01: Unused import — `sys` in `app.py`

**File:** `src/joy/app.py:4`
**Issue:** `import sys` is only referenced in `main()` via `sys.argv`. This is a legitimate use but
the import is at module level and triggers every time `JoyApp` is imported in tests (adds marginal
startup cost). No action strictly required; noted for completeness.

---

### IN-02: Magic number `0.1` in async test pauses

**File:** `tests/test_worktree_pane.py:174, 203, 229, 251, 263`
**Issue:** `await pilot.pause(0.1)` is scattered through multiple async tests with no explanation
of what 0.1 seconds represents. If Textual mount/refresh latency increases (e.g., on a slow CI
runner), tests relying on this hardcoded pause may become flaky. The companion integration tests
in the same file use `await app.workers.wait_for_complete()` which is the correct pattern.

**Fix:** After calling `pane.set_worktrees(...)` prefer `await pilot.pause()` with
`app.workers.wait_for_complete()`, or at minimum define a named constant:
```python
_TEXTUAL_SETTLE = 0.1  # seconds — wait for Textual async DOM mutations to settle
```

---

### IN-03: Docstring reference typo — "D-10" in `WorktreePane.set_worktrees`

**File:** `src/joy/widgets/worktree_pane.py:244`
**Issue:** The inline comment reads `# Group worktrees by repo_name — repos with no worktrees are
naturally hidden (D-10)` but `D-10` in the RESEARCH.md refers to "tab-cycling / focus", not to
the grouping/hiding behaviour. The grouping requirement is `D-04` or `D-11`. Minor; does not
affect behaviour.

**Fix:** Update comment to reference `D-11` (alphabetical repo order / hidden empty sections).

---

### IN-04: `test_worktree_order_alphabetical` — fragile branch-name extraction

**File:** `tests/test_worktree_pane.py:261`
**Issue:** The test extracts branch names with:
```python
branch_names = [str(row.content).split("\n")[0].strip() for row in rows]
```
This strips the leading icon (`\ue0a0`) and trailing dirty/no-upstream glyphs by relying on
`.strip()`, but if `build_content` changes its formatting (e.g., adds colour markup that expands
into the string representation), the extracted names will contain icon characters and the sort
assertion will fail with a confusing error message. The test couples directly to the internal
rendering format.

**Fix:** Add a `branch` attribute to `WorktreeRow` so tests can query it directly:
```python
class WorktreeRow(Static):
    def __init__(self, worktree: WorktreeInfo, *, display_path=None, **kwargs):
        self.worktree = worktree   # expose for test introspection
        ...
```
Then: `branch_names = [row.worktree.branch for row in rows]`.

---

_Reviewed: 2026-04-13T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
