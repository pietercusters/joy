---
phase: 20-widget-tests-snapshots
reviewed: 2026-05-08T00:00:00Z
depth: standard
files_reviewed: 8
files_reviewed_list:
  - pyproject.toml
  - tests/conftest.py
  - tests/fakes.py
  - tests/test_snapshots.py
  - tests/test_widget_project_detail.py
  - tests/test_widget_project_list.py
  - tests/test_widget_terminal_pane.py
  - tests/test_widget_worktree_pane.py
findings:
  critical: 0
  warning: 3
  info: 3
  total: 6
status: issues_found
---

# Phase 20: Code Review Report

**Reviewed:** 2026-05-08T00:00:00Z
**Depth:** standard
**Files Reviewed:** 8
**Status:** issues_found

## Summary

Phase 20 adds widget isolation tests (TEST-04) using a `FakeBackend` pattern and snapshot baseline tests (TEST-05) using `pytest-textual-snapshot`. The overall design is sound: Protocols are correctly declared `@runtime_checkable`, fake adapters are structurally verified at fixture time, and test isolation is enforced by the session-scoped `_isolated_store_paths` fixture.

Three warnings and three info items were found. No security or data-loss issues.

The most actionable findings are: a Protocol conformance gap in `FakeStorage.save_config` (silent no-op vs. tracked call), a `FakeTerminal.fetch_sessions` logic inversion that silently returns `None` for non-empty sessions, and fragile `pilot.pause` timing in the snapshot and widget tests that can produce flaky results.

---

## Warnings

### WR-01: FakeTerminal.fetch_sessions inverts the return condition

**File:** `tests/fakes.py:86`
**Issue:** The method returns `(sessions, live_tab_ids)` only when `self._sessions` is truthy, and `None` otherwise. This means a `FakeTerminal` initialised with sessions **correctly returns data**, but a `FakeTerminal()` with **no sessions** also returns `None` — which the production `TerminalPort` semantics reserve for "iTerm2 unavailable". Any future test that wants to express "iTerm2 is available but has no sessions" cannot be written with this fake: `FakeTerminal(sessions=[])` returns `None` instead of `([], set())`, misrepresenting the port contract.

```python
# current — incorrect for empty-but-available case
def fetch_sessions(self) -> tuple[list[TerminalSession], set[str]] | None:
    return (self._sessions, self._live_tab_ids) if self._sessions else None

# fix — use an explicit sentinel to distinguish "unavailable" from "no sessions"
class FakeTerminal:
    def __init__(
        self,
        sessions: list[TerminalSession] | None = None,
        live_tab_ids: set[str] | None = None,
        available: bool = True,   # new parameter
    ):
        self._sessions = sessions or []
        self._live_tab_ids = live_tab_ids or set()
        self._available = available
        ...

    def fetch_sessions(self) -> tuple[list[TerminalSession], set[str]] | None:
        if not self._available:
            return None
        return (self._sessions, self._live_tab_ids)
```

---

### WR-02: FakeStorage.save_config silently discards calls — inconsistent with save_projects tracking

**File:** `tests/fakes.py:45`
**Issue:** `save_projects` appends a copy to `self.saved_projects` so tests can assert on persistence calls. `save_config` is a silent no-op (just `pass`). If any widget test ever needs to verify that a config change was persisted, the fake provides no mechanism to do so — and there is no `saved_config` attribute to check. This inconsistency also risks hiding bugs where config saves are called unexpectedly or not called at all.

```python
# current
def save_config(self, config: Config) -> None:
    pass

# fix — track calls consistently
def __init__(self, ...):
    ...
    self.saved_configs: list[Config] = []

def save_config(self, config: Config) -> None:
    self.saved_configs.append(config)
```

Apply the same pattern to `save_repos` and `save_archived_projects` if those operations are ever tested.

---

### WR-03: Snapshot tests use fixed pilot.pause() timing — flaky on slow CI

**File:** `tests/test_snapshots.py:55-58`, `tests/test_snapshots.py:67-70`
**Issue:** `await pilot.pause(0.3)` followed by `await pilot.app.workers.wait_for_complete()` followed by another `await pilot.pause(0.2)` is a timing-based synchronisation strategy. The fixed durations were presumably tuned on the author's machine. On a slower CI runner the workers may not finish within 0.3 s, causing the snapshot to be taken before the app has fully rendered and producing a spurious baseline difference. `wait_for_complete()` is the correct synchronisation primitive — the surrounding pauses are redundant and risky.

```python
# current
async def run_before(pilot):
    await pilot.pause(0.3)
    await pilot.app.workers.wait_for_complete()
    await pilot.press("enter")
    await pilot.pause(0.2)

# fix — remove the timing-dependent pauses; keep only wait_for_complete
async def run_before(pilot):
    await pilot.app.workers.wait_for_complete()
    await pilot.press("enter")
    await pilot.app.workers.wait_for_complete()
```

The same applies to `test_snapshot_sync_active` (lines 67-70).

---

## Info

### IN-01: fakes.py comment says "Do NOT import joy.ports" but conftest.py does the isinstance check instead

**File:** `tests/fakes.py:4-5`, `tests/conftest.py:73-88`
**Issue:** The comment in `fakes.py` says "Do NOT import joy.ports in this file" to keep fakes self-contained. This constraint is honoured — `fakes.py` does not import from `joy.ports`. The Protocol conformance assertions (`isinstance(storage, StoragePort)`) are correctly placed in `conftest.py`. This is good design but is not documented anywhere except the comment; future contributors may be confused about why the constraint exists. A brief inline rationale would help.

**Fix:** Expand the comment in `fakes.py`:

```python
# Do NOT import joy.ports here. Fakes rely on structural subtyping (duck typing).
# Protocol isinstance checks live in conftest.py fixtures so this file stays
# import-cycle free and usable outside the test suite.
```

---

### IN-02: Widget tests access private `_cursor` attribute directly

**File:** `tests/test_widget_project_detail.py:77`, `tests/test_widget_project_list.py:79`, `tests/test_widget_terminal_pane.py:114`, `tests/test_widget_worktree_pane.py:91`
**Issue:** All four widget test files assert on `widget._cursor` — a private implementation attribute. This couples the tests to the internal representation. If the cursor is ever renamed or refactored to a property, all four tests will silently fail to import or raise `AttributeError` rather than providing a helpful test failure message. The pattern is consistent and deliberate (all four tests follow the same style), so this is an info-level observation rather than a blocking issue.

**Fix:** Either expose a `cursor` (or `selected_index`) read-only property on each widget and assert on that, or document the convention in a test comment to make the coupling explicit:

```python
# _cursor is the widget's internal row index. Accessing it directly here
# because no public cursor property exists yet.
assert detail._cursor == 1
```

---

### IN-03: `iterm2>=2.15` in production dependencies; only used in tests via FakeTerminal

**File:** `pyproject.toml:12`
**Issue:** `iterm2>=2.15` is listed as a production dependency in `[project.dependencies]`. The iTerm2 Python API is a heavy optional integration — it requires a running iTerm2 daemon and is macOS-specific. If it cannot be imported in a plain Python environment (e.g., Linux CI, fresh macOS install without iTerm2), the package installation will succeed but imports may fail at runtime if the `iterm2` package has non-trivial requirements. Additionally, the Phase 20 tests use `FakeTerminal` specifically to avoid this dependency in tests, suggesting the intent is to not require it at import time. This should be an optional or extra dependency, not a hard runtime one.

**Fix:** Move to an optional group or use a try/except import in the production code that uses it:

```toml
# option A: move to an extras group
[project.optional-dependencies]
iterm2 = ["iterm2>=2.15"]

# option B: keep as dev dependency and guard the import in terminal_sessions.py
try:
    import iterm2
except ImportError:
    iterm2 = None
```

---

_Reviewed: 2026-05-08T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
