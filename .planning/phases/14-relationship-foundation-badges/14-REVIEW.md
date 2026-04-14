---
phase: 14-relationship-foundation-badges
reviewed: 2026-04-14T00:00:00Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - src/joy/app.py
  - src/joy/resolver.py
  - src/joy/widgets/project_list.py
  - src/joy/widgets/terminal_pane.py
  - src/joy/widgets/worktree_pane.py
  - tests/test_project_list.py
  - tests/test_resolver.py
  - tests/test_terminal_pane.py
  - tests/test_worktree_pane_cursor.py
findings:
  critical: 0
  warning: 5
  info: 4
  total: 9
status: issues_found
---

# Phase 14: Code Review Report

**Reviewed:** 2026-04-14
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

The Phase 14 implementation adds cross-pane relationship resolution (resolver.py), badge display on ProjectList rows, and cursor-identity preservation on both TerminalPane and WorktreePane. The overall design is sound: the two-flag pattern is correctly single-threaded (Textual main loop serializes `call_from_thread` callbacks, so no asyncio coordination needed), the resolver is a clean pure function, and the cursor preservation logic (identity-then-clamp) is correctly implemented in both panes.

Five warnings and four info-level findings are noted. None are security issues. The most impactful warnings are: a `startswith` home-prefix bug that silently corrupts path display for users whose home directory is a prefix of another user's home (macOS multi-user or unusual home paths), a silent swallowing of all exceptions in `_update_badges`, a stale-data window in the two-flag pattern when concurrent refresh cycles interleave, and a resolver collision where duplicate (repo, branch) BRANCH objects overwrite silently.

---

## Warnings

### WR-01: `abbreviate_home` matches home as bare string prefix, not directory boundary

**File:** `src/joy/widgets/terminal_pane.py:46` and `src/joy/widgets/worktree_pane.py:47`
**Issue:** Both `_abbreviate_home` (terminal_pane) and `abbreviate_home` (worktree_pane) check `path_str.startswith(home)` where `home = str(Path.home())`. On macOS, `Path.home()` returns a path without a trailing slash (e.g. `/Users/pieter`). A path like `/Users/pieter2/project` or `/Users/pieterbackup` would pass the startswith check and produce corrupted output: `~2/project` or `~backup`. This would affect any machine where a sibling directory shares the home prefix — e.g. multi-user Macs with usernames like `pieter` and `pieterj`.

**Fix:** Require a `/` after the home prefix, or use `Path` object containment:
```python
# terminal_pane.py line 46 / worktree_pane.py line 47
home = str(Path.home())
if path_str == home:
    return "~"
if path_str.startswith(home + "/"):
    return "~" + path_str[len(home):]
return path_str
```

---

### WR-02: `_update_badges` silently swallows all exceptions

**File:** `src/joy/app.py:216-219`
**Issue:** The bare `except Exception: pass` swallows any exception from `update_badges` or `RelationshipIndex.worktrees_for` / `agents_for`. The comment says "ProjectList not yet mounted", but this exception handler will also hide bugs in the resolver output, type errors in `RelationshipIndex`, and logic errors in `ProjectRow.set_counts`. A real bug in Phase 14's badge update path would be completely invisible.
```python
    except Exception:
        pass  # ProjectList not yet mounted — badges will be populated on next cycle
```
**Fix:** Narrow the catch to the specific exception that mounting raises (`NoMatches` or `textual.css.query.NoMatches`):
```python
from textual.css.query import NoMatches
try:
    self.query_one(ProjectList).update_badges(self._rel_index)
except NoMatches:
    pass  # ProjectList not yet mounted — badges will be populated on next cycle
```

---

### WR-03: Two-flag pattern leaves `_worktrees_ready=True` when out-of-order concurrent cycles interleave

**File:** `src/joy/app.py:191-210`
**Issue:** When two concurrent worktree refresh cycles run (e.g. timer fires while a manual 'r' refresh is still in-flight), the older cycle's `_set_worktrees` callback can arrive on the main thread after the newer cycle has already been fully processed. Sequence:

1. Cycle A (older): `_set_worktrees` sets `_current_worktrees=A`, `_worktrees_ready=True` — sessions not ready, returns.
2. Cycle A: `_set_terminal_sessions` sets `_current_sessions=A`, `_sessions_ready=True` — both ready, `_maybe_compute_relationships` fires, **resets both flags**, computes with (A, A). Correct.
3. Cycle B (newer) worktrees arrive late: `_set_worktrees` sets `_current_worktrees=B`, `_worktrees_ready=True`.
4. **`_sessions_ready` is False** (reset in step 2). `_maybe_compute_relationships` returns immediately.
5. Cycle B's `_set_terminal_sessions` never fires (already complete) — `_worktrees_ready` stays `True` indefinitely.

Result: stale worktree data (`_current_worktrees=B`) and `_worktrees_ready=True` sit until the next timer cycle brings a fresh session refresh. The relationship index is not recomputed for up to one full `refresh_interval`. In practice the interval is short (default ~30s), so impact is low, but it is a correctness gap.

**Fix:** The simplest mitigation is to track a cycle counter and discard results from superseded cycles, or to always reset `_worktrees_ready=False` at the start of `_set_worktrees` (before setting it to `True`) — but that changes semantics. The minimal fix is a comment documenting the known race and confirming it is tolerated:

```python
def _maybe_compute_relationships(self) -> None:
    """...
    NOTE: Out-of-order arrival of concurrent refresh cycles can leave
    _worktrees_ready=True after the paired sessions callback has already
    fired. This is tolerated: the next timer cycle will resync.
    """
```

Alternatively, add a cycle counter per worker to detect and skip stale arrivals.

---

### WR-04: Resolver silently overwrites duplicate BRANCH/WORKTREE objects across projects

**File:** `src/joy/resolver.py:81-86`
**Issue:** In Pass 1 of `compute_relationships`, if two projects declare the same path as a WORKTREE object, or if two projects sharing the same repo declare the same branch as a BRANCH object, the later project in the list silently overwrites the earlier:
```python
path_to_project[obj.value] = project        # line 81 — last writer wins
branch_to_project[(project.repo, obj.value)] = project  # line 84 — same
```
The first project loses its relationship silently. The worktree is matched to the second project only. Badges on the first project will show 0 worktrees even though it has a WORKTREE object pointing to a real worktree. There is no warning to the user.

**Fix:** Log a warning (or store a conflict marker) when a collision is detected:
```python
if obj.kind == PresetKind.WORKTREE:
    if obj.value in path_to_project:
        # Collision: two projects claim the same worktree path.
        # Policy: last declaration wins. Consider surfacing this to the user.
        pass
    path_to_project[obj.value] = project
```
For v1, documenting the "last writer wins" policy in a docstring is an acceptable mitigation if collision is considered user-error.

---

### WR-05: `action_delete_project` directly mutates `ProjectDetail` private internals

**File:** `src/joy/widgets/project_list.py:311-318`
**Issue:** When the last project is deleted, the handler directly sets `detail._project = None`, `detail._rows = []`, `detail._cursor = -1`, and calls `detail.query_one("#detail-scroll").remove_children()`. This bypasses any clearing logic in `ProjectDetail.set_project` (or equivalent), tightly coupling `ProjectList` to `ProjectDetail` implementation details. If `ProjectDetail` adds new state fields in a future phase, this clear path will silently leave stale state.

**Fix:** Add a `clear()` method to `ProjectDetail` and call it here:
```python
# In ProjectDetail:
def clear(self) -> None:
    """Reset to empty state — called when the last project is deleted."""
    self._project = None
    self._rows = []
    self._cursor = -1
    self.query_one("#detail-scroll").remove_children()

# In project_list.py action_delete_project:
detail = self.app.query_one("#project-detail", ProjectDetail)
detail.clear()
```

---

## Info

### IN-01: `update_badges` parameter typed as `object` with type-ignore comments

**File:** `src/joy/widgets/project_list.py:422-430`
**Issue:** `update_badges(self, index: object)` uses `object` as the parameter type and calls `index.worktrees_for()` and `index.agents_for()` with `# type: ignore[union-attr]` suppressions. The lazy import `from joy.resolver import RelationshipIndex` inside the function is never used for narrowing. This defeats static type checking for the most critical Phase 14 integration point.
**Fix:** Type the parameter as `RelationshipIndex` directly and move the import to the top of the file (or keep it lazy but use it):
```python
def update_badges(self, index: "RelationshipIndex") -> None:
```

---

### IN-02: `test_project_row_set_counts_both` assertion is digit-fragile

**File:** `tests/test_project_list.py:58`
**Issue:** `assert "5" in content and "3" in content` would pass spuriously if `agent_count=13` (the `"3"` matches inside `"13"`). The test is not wrong for the current values but is fragile if counts are ever changed to multi-digit numbers in test setup.
**Fix:** Use exact substring matching for the badge format:
```python
assert f"{ICON_BRANCH} 5" in content
assert f"{ICON_CLAUDE} 3" in content
```

---

### IN-03: `test_claude_sessions_sorted_alphabetically` does not exercise the busy-first sort priority

**File:** `tests/test_terminal_pane.py:619-644`
**Issue:** All three sessions in the test have `foreground_process="claude"` (default for `_claude_session`). Since `"claude"` is not in `_SHELL_PROCESSES`, all are `is_busy=True`, giving sort key `(0, name)`. The test verifies alphabetical order but never exercises the `is_busy=False` branch (sort key `(1, name)`) or the mixed-priority ordering (busy before waiting). A waiting claude session would be sorted after all busy ones regardless of name, but this is not tested.
**Fix:** Add a companion test with mixed busy/waiting sessions:
```python
def test_claude_sessions_busy_before_waiting():
    """Busy (non-shell foreground) Claude sessions appear before waiting ones."""
    sessions = [
        _claude_session("c1", "alpha-waiting", foreground_process="zsh"),  # waiting
        _claude_session("c2", "beta-busy",    foreground_process="claude"),  # busy
    ]
    # after set_sessions: beta-busy (index 0) before alpha-waiting (index 1)
```

---

### IN-04: No unit test exercises the two-flag pattern in `_maybe_compute_relationships`

**File:** `src/joy/app.py:191-210`
**Issue:** The two-flag ready pattern and `compute_relationships` call path in `_maybe_compute_relationships` have no direct tests. The resolver itself is well-tested in `test_resolver.py`, but the integration path (both flags set → compute → badges updated) is only exercised via full app integration, which is not in the test suite. A regression in flag reset order or badge push would not be caught.
**Fix:** Add a unit test that directly calls `_maybe_compute_relationships` with pre-set flags and asserts that `_rel_index` is populated and `_update_badges` is invoked:
```python
def test_maybe_compute_relationships_fires_when_both_ready(monkeypatch):
    app = JoyApp()
    app._worktrees_ready = True
    app._sessions_ready = True
    called = []
    monkeypatch.setattr(app, "_update_badges", lambda: called.append(True))
    app._maybe_compute_relationships()
    assert called == [True]
    assert app._worktrees_ready is False
    assert app._sessions_ready is False
```

---

_Reviewed: 2026-04-14_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
