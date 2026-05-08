# Phase 20: Widget Tests & Snapshots - Pattern Map

**Mapped:** 2026-05-08
**Files analyzed:** 8 new/modified files
**Analogs found:** 8 / 8

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `tests/fakes.py` | utility (test doubles) | request-response | `tests/test_ports.py` (inline fakes) + `tests/test_pane_coordinator.py` (fake panes) | exact — same fake-object pattern, extracted into module |
| `tests/conftest.py` | config (test fixtures) | — | `tests/conftest.py` (existing, lines 1-61) | exact — extend existing file |
| `tests/test_widget_project_list.py` | test (widget pilot) | request-response | `tests/test_terminal_pane.py` | exact — same minimal-TestApp + asyncio + pilot pattern |
| `tests/test_widget_project_detail.py` | test (widget pilot) | request-response | `tests/test_terminal_pane.py` | exact |
| `tests/test_widget_worktree_pane.py` | test (widget pilot) | request-response | `tests/test_worktree_pane.py` | exact — same file superseded; new file uses `@pytest.mark.asyncio` not `asyncio.run()` |
| `tests/test_widget_terminal_pane.py` | test (widget pilot) | request-response | `tests/test_terminal_pane.py` | exact — same file superseded; new file uses `@pytest.mark.asyncio` |
| `tests/test_snapshots.py` | test (snapshot) | request-response | `tests/test_tui.py` (store-mock fixture pattern, lines 46-62) | role-match — adds `snap_compare` over the store-mock fixture |
| `pyproject.toml` | config | — | `pyproject.toml` (existing, lines 21-34) | exact — extend pytest markers, change version constraint |

---

## Pattern Assignments

### `tests/fakes.py` (utility, test doubles)

**Analogs:**
- `tests/test_pane_coordinator.py` lines 18-70 (FakeWorktreePane, FakeTerminalPane, FakeProjectList, FakeDetailPane)
- `tests/test_ports.py` lines 17-73 (inline FakeStorage, FakeGitData, FakeTerminal, FakeOpener — used for Protocol conformance only)

**Module-level docstring pattern** (`tests/test_pane_coordinator.py` lines 1-5):
```python
"""Fake backend adapter classes for Phase 20 widget pilot tests.

All fakes conform to Protocol contracts defined in joy.ports.
Do NOT import joy.ports in this file -- conformance is structural (duck typing).
"""
from __future__ import annotations
```

**FakeStorage pattern** (derived from `tests/test_ports.py` lines 17-30 and RESEARCH.md):
```python
class FakeStorage:
    """Fake StoragePort: returns canned data, tracks save calls."""
    def __init__(self, projects=None, config=None, repos=None):
        self.projects = projects or []
        self.config = config or Config()
        self.repos = repos or []
        self.saved_projects: list[list] = []

    def load_projects(self): return self.projects
    def save_projects(self, projects): self.saved_projects.append(list(projects))
    def load_config(self): return self.config
    def save_config(self, config): pass
    def load_repos(self): return self.repos
    def save_repos(self, repos): pass
    def load_archived_projects(self): return []
    def save_archived_projects(self, projects): pass
```

**FakeTerminal pattern** (derived from `tests/test_ports.py` lines 47-58):
```python
class FakeTerminal:
    """Fake TerminalPort: no iTerm2 subprocess calls, tracks activations."""
    def __init__(self, sessions=None, live_tab_ids=None):
        self._sessions = sessions or []
        self._live_tab_ids = live_tab_ids or set()
        self.activated: list[str] = []

    def fetch_sessions(self):
        return (self._sessions, self._live_tab_ids) if self._sessions else None
    def create_tab(self, name): return None
    def activate_session(self, session_id):
        self.activated.append(session_id)
        return True
    def close_session(self, session_id, *, force=False): return True
    def close_tab(self, tab_id, *, force=False): return True
    def create_session(self, name): return None
    def rename_session(self, session_id, new_name): return True
```

**FakeGitData pattern** (derived from `tests/test_ports.py` lines 47-49):
```python
class FakeGitData:
    """Fake GitDataPort: returns canned worktrees, no subprocess."""
    def __init__(self, worktrees=None):
        self._worktrees = worktrees or []

    def discover_worktrees(self, repos, branch_filter):
        return self._worktrees
```

**FakeOpener pattern** (derived from `tests/test_ports.py` lines 62-64):
```python
class FakeOpener:
    """Fake OpenerPort: records open_object calls without subprocess."""
    def __init__(self):
        self.opened: list[tuple] = []

    def open_object(self, *, item, config):
        self.opened.append((item, config))
```

---

### `tests/conftest.py` (extend existing file)

**Analog:** `tests/conftest.py` lines 1-61 (existing — add fixtures after existing content)

**Existing file pattern to preserve** (lines 1-61):
```python
"""Shared test fixtures for joy tests."""
from datetime import date
import pytest
from joy.models import Config, ObjectItem, PresetKind, Project

@pytest.fixture
def sample_config() -> Config: ...

@pytest.fixture
def sample_object() -> ObjectItem: ...

@pytest.fixture
def sample_project(sample_object: ObjectItem) -> Project: ...

@pytest.fixture(autouse=True, scope="session")
def _isolated_store_paths(tmp_path_factory): ...
```

**New FakeBackend fixture pattern** to add (derived from RESEARCH.md + `tests/test_ports.py` Protocol conformance check pattern):
```python
@pytest.fixture
def fake_storage(sample_project):
    """FakeStorage pre-loaded with sample_project."""
    from tests.fakes import FakeStorage
    from joy.ports import StoragePort
    storage = FakeStorage(projects=[sample_project])
    assert isinstance(storage, StoragePort)  # runtime Protocol check
    return storage


@pytest.fixture
def fake_terminal():
    """FakeTerminal with no sessions (iTerm2 unavailable simulation)."""
    from tests.fakes import FakeTerminal
    from joy.ports import TerminalPort
    terminal = FakeTerminal()
    assert isinstance(terminal, TerminalPort)
    return terminal


@pytest.fixture
def fake_git_data():
    """FakeGitData returning empty worktrees by default."""
    from tests.fakes import FakeGitData
    from joy.ports import GitDataPort
    git_data = FakeGitData()
    assert isinstance(git_data, GitDataPort)
    return git_data
```

---

### `tests/test_widget_project_list.py` (test, widget pilot)

**Analog:** `tests/test_terminal_pane.py` (most complete example of the minimal-TestApp + pilot pattern)

**File header pattern** (`tests/test_terminal_pane.py` lines 1-10):
```python
"""Tests for Phase 20: ProjectList widget with FakeBackend injection (TEST-04)."""
from __future__ import annotations

import pytest
from textual.app import App, ComposeResult

from joy.models import Config, ObjectItem, PresetKind, Project, Repo
from joy.widgets.project_list import ProjectList, ProjectRow, GroupHeader
```

**Minimal TestApp pattern** (`tests/test_terminal_pane.py` lines 188-196 — `_TestApp` inner class):
```python
class _ProjectListTestApp(App):
    """Minimal app for testing ProjectList in isolation."""
    def compose(self) -> ComposeResult:
        yield ProjectList(id="project-list")
```

**Sample data helper pattern** (`tests/test_terminal_pane.py` lines 28-41):
```python
def _sample_projects() -> list[Project]:
    return [
        Project(name="alpha", objects=[
            ObjectItem(kind=PresetKind.BRANCH, value="main"),
        ]),
        Project(name="beta", objects=[]),
    ]
```

**Async pilot test pattern** (`tests/test_terminal_pane.py` lines 205-228 — `test_set_sessions_renders_session_rows`):
```python
@pytest.mark.asyncio
async def test_project_list_renders_rows():
    """ProjectList renders ProjectRow for each project."""
    app = _ProjectListTestApp()
    async with app.run_test() as pilot:
        plist = app.query_one(ProjectList)
        plist.set_projects(_sample_projects(), [])
        await pilot.pause(0.1)
        rows = app.query(ProjectRow)
        assert len(rows) == 2
```

**Cursor navigation test pattern** (`tests/test_terminal_pane.py` lines 391-413 — `test_cursor_navigation_j_moves_down`):
```python
@pytest.mark.asyncio
async def test_project_list_cursor_down():
    """Pressing 'j' moves cursor from 0 to 1."""
    app = _ProjectListTestApp()
    async with app.run_test() as pilot:
        plist = app.query_one(ProjectList)
        plist.set_projects(_sample_projects(), [])
        await pilot.pause(0.1)
        plist.focus()
        await pilot.press("j")
        assert plist._cursor == 1
```

**Key to avoid:** Do NOT use `asyncio.run()` wrapper (deprecated pattern from `tests/test_terminal_pane.py` lines 193-227 old-style). Always use `@pytest.mark.asyncio` + `async def`.

---

### `tests/test_widget_project_detail.py` (test, widget pilot)

**Analog:** `tests/test_terminal_pane.py` (same minimal-TestApp + pilot pattern)

**Imports pattern** (same as terminal_pane analog):
```python
"""Tests for Phase 20: ProjectDetail widget (TEST-04)."""
from __future__ import annotations

import pytest
from textual.app import App, ComposeResult

from joy.models import Config, ObjectItem, PresetKind, Project
from joy.widgets.project_detail import ProjectDetail
```

**Minimal TestApp pattern:**
```python
class _ProjectDetailTestApp(App):
    def compose(self) -> ComposeResult:
        yield ProjectDetail(id="project-detail")
```

**set_project call pattern** — ProjectDetail accepts a Project via `set_project()` method (same call pattern as `pane.set_sessions()` in terminal tests, lines 218-225):
```python
@pytest.mark.asyncio
async def test_project_detail_renders_objects():
    """ProjectDetail renders ObjectRow for each project object."""
    app = _ProjectDetailTestApp()
    async with app.run_test() as pilot:
        detail = app.query_one(ProjectDetail)
        detail.set_project(sample_project)
        await pilot.pause(0.1)
        # assert ObjectRow widgets present
```

---

### `tests/test_widget_worktree_pane.py` (test, widget pilot)

**Analog:** `tests/test_worktree_pane.py` (existing — new file replaces `asyncio.run()` with `@pytest.mark.asyncio`)

**Old pattern to NOT copy** (`tests/test_worktree_pane.py` lines 165-184 — `test_grouping_by_repo`):
```python
# OLD PATTERN — DO NOT COPY
def test_grouping_by_repo():
    import asyncio
    async def _run():
        app = _TestApp()
        async with app.run_test() as pilot:
            ...
    asyncio.run(_run())  # <-- deprecated, causes event loop conflicts
```

**New pattern to use** (`tests/test_worktree_pane.py` lines 384-398 — `test_loading_placeholder`, which already uses `@pytest.mark.asyncio`):
```python
@pytest.mark.asyncio
async def test_worktree_pane_renders_groups():
    """WorktreePane renders one GroupHeader per distinct repo_name."""
    from textual.app import App, ComposeResult
    from joy.widgets.worktree_pane import WorktreePane, WorktreeRow, GroupHeader
    from joy.models import WorktreeInfo

    class _TestApp(App):
        def compose(self) -> ComposeResult:
            yield WorktreePane()

    app = _TestApp()
    async with app.run_test() as pilot:
        pane = app.query_one(WorktreePane)
        await pane.set_worktrees(_sample_worktrees())
        await pilot.pause(0.1)
        headers = pane.query(GroupHeader)
        assert len(headers) == 2
```

**Sample data pattern** (`tests/test_worktree_pane.py` lines 43-74 — `_sample_worktrees()`):
```python
def _sample_worktrees() -> list[WorktreeInfo]:
    return [
        WorktreeInfo(repo_name="joy", branch="feat-z", path="/tmp/joy/wt/feat-z", is_dirty=True),
        WorktreeInfo(repo_name="joy", branch="feat-a", path="/tmp/joy/wt/feat-a", is_dirty=False),
        WorktreeInfo(repo_name="other", branch="develop", path="/tmp/other/wt/develop"),
    ]
```

---

### `tests/test_widget_terminal_pane.py` (test, widget pilot)

**Analog:** `tests/test_terminal_pane.py` (existing — refactor asyncio.run() tests to `@pytest.mark.asyncio`)

This new file is a higher-quality rewrite of the async tests in the existing file. The unit tests (lines 82-183 in the analog — no app needed) can be copied verbatim. The async tests (lines 185-787) should be rewritten using `@pytest.mark.asyncio` instead of `asyncio.run()`.

**Pattern difference — existing (broken style)** (`tests/test_terminal_pane.py` lines 192-227):
```python
def test_set_sessions_renders_session_rows():    # sync def wrapping async
    ...
    async def _run():
        async with app.run_test() as pilot:
            ...
    asyncio.run(_run())   # <-- do not copy
```

**New canonical style** (from `tests/test_worktree_pane.py` lines 384-409 — already uses asyncio marker):
```python
@pytest.mark.asyncio
async def test_set_sessions_renders_session_rows():
    app = _TerminalTestApp()
    async with app.run_test() as pilot:
        pane = app.query_one(TerminalPane)
        await pane.set_sessions(_fake_sessions())
        await pilot.pause(0.1)
        rows = pane.query(SessionRow)
        assert len(rows) == 2
```

**FakeTerminal injection for action tests** — replace `@patch("joy.terminal_sessions.activate_session")` with FakeTerminal tracking:
```python
# Old pattern (test_terminal_pane.py lines 509-524):
with patch("joy.terminal_sessions.activate_session", return_value=True) as mock_activate:
    ...
    mock_activate.assert_called_once_with("session-id-abc")

# New pattern (Phase 20 — inject FakeTerminal via constructor or track via fake):
fake_term = FakeTerminal(sessions=[_make_session("session-id-abc", "session-a")])
# Then assert fake_term.activated == ["session-id-abc"]
```

**Note:** If TerminalPane does not yet accept a terminal port constructor arg (widgets get data via `set_sessions()`, not constructor injection per Open Question 1 in RESEARCH.md), use the direct-method-injection approach: call `pane.set_sessions()` with FakeTerminal-supplied data, and for action tests that trigger iTerm2 calls, continue using `@patch` on the specific function — this is the pragmatic exception documented in RESEARCH.md Pitfall 2.

---

### `tests/test_snapshots.py` (test, snapshot)

**Analog:** `tests/test_tui.py` lines 46-62 (store-mock fixture + JoyApp pilot)

**Imports + store mock pattern** (`tests/test_tui.py` lines 1-62):
```python
"""Snapshot baseline tests for joy TUI (Phase 20, TEST-05)."""
from __future__ import annotations

import pytest
from unittest.mock import patch

from joy.app import JoyApp
from joy.models import Config, ObjectItem, PresetKind, Project

pytestmark = pytest.mark.snapshot
```

**_mock_store fixture pattern** (`tests/test_tui.py` lines 46-62):
```python
_PROJECTS = [
    Project(name="project-alpha", objects=[
        ObjectItem(kind=PresetKind.BRANCH, value="main"),
        ObjectItem(kind=PresetKind.MR, value="https://gitlab.com/owner/repo/-/merge_requests/1", label="MR #1"),
    ]),
    Project(name="project-beta", objects=[
        ObjectItem(kind=PresetKind.TICKET, value="https://notion.so/123", label="TICK-1"),
    ]),
]


def _mock_store():
    """Patch store module functions to return deterministic test data."""
    return patch.multiple(
        "joy.store",
        load_projects=lambda: _PROJECTS,
        load_config=lambda: Config(),
        load_repos=lambda: [],
    )
```

**Snapshot test pattern** (RESEARCH.md Code Examples + `tests/test_tui.py` fixture structure):
```python
def test_snapshot_initial_render(snap_compare):
    """Snapshot baseline: initial render with two projects loaded."""
    with _mock_store():
        assert snap_compare(JoyApp(), terminal_size=(120, 40))


def test_snapshot_project_selected(snap_compare):
    """Snapshot baseline: first project selected, detail pane populated."""
    async def run_before(pilot):
        await pilot.pause(0.3)
        await pilot.app.workers.wait_for_complete()
        await pilot.press("enter")
        await pilot.pause(0.2)

    with _mock_store():
        assert snap_compare(JoyApp(), run_before=run_before, terminal_size=(120, 40))


def test_snapshot_sync_active(snap_compare):
    """Snapshot baseline: worktree pane visible with sync state."""
    async def run_before(pilot):
        await pilot.pause(0.3)
        await pilot.app.workers.wait_for_complete()
        await pilot.pause(0.2)

    with _mock_store():
        assert snap_compare(JoyApp(), run_before=run_before, terminal_size=(120, 40))
```

**Critical:** `snap_compare` is a sync fixture from pytest-textual-snapshot. Do NOT mark snapshot tests with `@pytest.mark.asyncio` — the `run_before` async callback is handled internally by `snap_compare`.

---

### `pyproject.toml` (config, pytest dependencies)

**Analog:** `pyproject.toml` lines 21-34 (existing `[tool.pytest.ini_options]` section)

**Existing section** (lines 21-34):
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
addopts = ["-m", "not slow and not macos_integration"]
markers = [
    "macos_integration: tests requiring live macOS apps (iTerm2, Notion, etc.)",
    "slow: tests using Textual pilot (async TUI driver, 6-12s each) -- run with -m slow",
]

[dependency-groups]
dev = [
    "pytest>=9.0.3",
    "pytest-asyncio>=0.25",
]
```

**Required changes:**
1. Change `"pytest>=9.0.3"` to `"pytest>=8.4,<9"` (syrupy 4.8.0 requires pytest<9)
2. Add `"pytest-textual-snapshot>=1.1.0"` to dev dependencies
3. Add `snapshot` marker to `markers` list
4. Add `not snapshot` to `addopts` `-m` expression

**Target section:**
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
addopts = ["-m", "not slow and not macos_integration and not snapshot"]
markers = [
    "macos_integration: tests requiring live macOS apps (iTerm2, Notion, etc.)",
    "slow: tests using Textual pilot (async TUI driver, 6-12s each) -- run with -m slow",
    "snapshot: snapshot baseline tests using pytest-textual-snapshot -- run with -m snapshot",
]

[dependency-groups]
dev = [
    "pytest>=8.4,<9",
    "pytest-asyncio>=0.25",
    "pytest-textual-snapshot>=1.1.0",
]
```

---

## Shared Patterns

### Minimal TestApp wrapper
**Source:** `tests/test_terminal_pane.py` lines 188-196, `tests/test_worktree_pane.py` lines 167-172
**Apply to:** All `test_widget_*.py` files

```python
from textual.app import App, ComposeResult

class _<Widget>TestApp(App):
    """Minimal app for testing <Widget> in isolation."""
    def compose(self) -> ComposeResult:
        yield <Widget>()
```

The leading underscore is the project convention for test-internal helper classes. Do NOT import widget factories at module level inside the class definition — import at the top of the test file.

### Async pilot test skeleton
**Source:** `tests/test_worktree_pane.py` lines 384-409 (the `@pytest.mark.asyncio` tests at the bottom)
**Apply to:** All `test_widget_*.py` async tests

```python
@pytest.mark.asyncio
async def test_<behavior>():
    """<What> <does what> <under what condition>."""
    app = _<Widget>TestApp()
    async with app.run_test() as pilot:
        widget = app.query_one(<Widget>)
        <call set_* method with test data>
        await pilot.pause(0.1)
        <assert DOM state>
```

### Store isolation (existing, shared)
**Source:** `tests/conftest.py` lines 46-61
**Apply to:** All test files that instantiate JoyApp (snapshot tests)

The `_isolated_store_paths` fixture is `autouse=True, scope="session"` — it patches path constants but does NOT mock `load_projects()`/`load_config()` function calls. Snapshot tests still need `patch.multiple("joy.store", ...)` to prevent actual file I/O.

### Protocol conformance assertion
**Source:** `tests/test_ports.py` lines 17-31
**Apply to:** `tests/conftest.py` fake fixture factories

```python
assert isinstance(fake, StoragePort)   # verify structural conformance at fixture creation
```

Use `@runtime_checkable` Protocols from `joy.ports`. The project already has all five Protocol classes as `@runtime_checkable`.

---

## No Analog Found

All files have analogs. No gaps.

| File | Notes |
|------|-------|
| `tests/fakes.py` | Assembled from inline fake classes scattered across `test_pane_coordinator.py` and `test_ports.py` — extracting into a module, not inventing patterns |

---

## Metadata

**Analog search scope:** `tests/`, `src/joy/widgets/`, `src/joy/ports.py`, `pyproject.toml`
**Files scanned:** 29 test files + 10 widget files + ports.py + pyproject.toml
**Pattern extraction date:** 2026-05-08
