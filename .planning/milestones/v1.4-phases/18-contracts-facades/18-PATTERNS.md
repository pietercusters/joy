# Phase 18: Contracts & Facades - Pattern Map

**Mapped:** 2026-05-07
**Files analyzed:** 8 (1 new, 7 modified)
**Analogs found:** 8 / 8

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/joy/ports.py` | contract | type-definition | `src/joy/models.py` | role-match |
| `src/joy/app.py` | controller | request-response | (self -- refactor in place) | exact |
| `src/joy/resolver.py` | service | transform | (self -- add properties) | exact |
| `src/joy/widgets/project_detail.py` | component | request-response | `src/joy/widgets/worktree_pane.py` | exact |
| `src/joy/widgets/project_list.py` | component | request-response | `src/joy/widgets/worktree_pane.py` | exact |
| `src/joy/widgets/worktree_pane.py` | component | request-response | (self -- add properties) | exact |
| `src/joy/widgets/terminal_pane.py` | component | request-response | `src/joy/widgets/worktree_pane.py` | exact |
| `tests/test_ports.py` | test | unit | `tests/test_resolver.py` | exact |

## Pattern Assignments

### `src/joy/ports.py` (contract, type-definition) -- NEW FILE

**Analog:** `src/joy/models.py`

**Imports pattern** (models.py lines 1-7):
```python
"""Pure data models for joy. No I/O, no side effects."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
```

For ports.py, the equivalent pattern is:
```python
"""Protocol contracts for joy service boundaries. No I/O, no side effects."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from joy.models import (
    ArchivedProject, Config, ObjectItem, Project, Repo,
    TerminalSession, WorktreeInfo,
)
```

**Key convention:** models.py uses `from __future__ import annotations` (line 1). Every source file in the project uses this. ports.py must too.

**Import rule:** ports.py imports ONLY from `joy.models`. No other joy modules. This prevents circular imports and enforces ARCH-01.

**Module-level docstring pattern** (models.py line 1):
```python
"""Pure data models for joy. No I/O, no side effects."""
```

**Class definition pattern** -- models.py uses `@dataclass` classes; ports.py uses `@runtime_checkable class ... (Protocol)`:
```python
@runtime_checkable
class StoragePort(Protocol):
    """Contract for project/config persistence."""

    def load_projects(self) -> list[Project]: ...
    def save_projects(self, projects: list[Project]) -> None: ...
```

**Method signatures to extract from existing module-level functions:**

StoragePort (from `src/joy/store.py`):
- `load_projects` (line 104): `(*, path: Path = PROJECTS_PATH) -> list[Project]` -- Protocol version drops the `path` parameter (implementation detail)
- `save_projects` (line 113): `(projects: list[Project], *, path: Path = PROJECTS_PATH) -> None`
- `load_config` (line 120): `(*, path: Path = CONFIG_PATH) -> Config`
- `save_config` (line 141): `(config: Config, *, path: Path = CONFIG_PATH) -> None`
- `load_repos` (line 183): `(*, path: Path = REPOS_PATH) -> list[Repo]`
- `save_repos` (line 193): `(repos: list[Repo], *, path: Path = REPOS_PATH) -> None`
- `load_archived_projects` (line 274): `(*, path: Path = ARCHIVE_PATH) -> list[ArchivedProject]`
- `save_archived_projects` (line 283): `(projects: list[ArchivedProject], *, path: Path = ARCHIVE_PATH) -> None`

GitDataPort (from `src/joy/worktrees.py`):
- `discover_worktrees` (line 9+ in module): `(repos: list[Repo], branch_filter: list[str]) -> list[WorktreeInfo]`

TerminalPort (from `src/joy/terminal_sessions.py`):
- `fetch_sessions`: `() -> tuple[list[TerminalSession], set[str]] | None`
- `create_tab`: `(name: str) -> str | None`
- `activate_session`: `(session_id: str) -> None`
- `close_session`: `(session_id: str, *, force: bool) -> bool`
- `close_tab`: `(tab_id: str, *, force: bool) -> None`
- `create_session`: `(name: str) -> str | None`
- `rename_session`: `(session_id: str, new_name: str) -> bool`

OpenerPort (from `src/joy/operations.py` line 22):
- `open_object`: `(*, item: ObjectItem, config: Config) -> None`

---

### `src/joy/app.py` (controller, request-response) -- MODIFIED

**Analog:** Self (refactor in place)

**Private-to-public facade pattern** -- JoyApp needs public properties and methods wrapping existing private attributes. Use the same property pattern already in the codebase (e.g., `highlighted_object` in project_detail.py lines 416-421):

```python
@property
def highlighted_object(self) -> ObjectItem | None:
    """Return the currently highlighted ObjectItem, or None if no cursor."""
    if self._project and 0 <= self._cursor < len(self._rows):
        return self._rows[self._cursor].item
    return None
```

**New public properties on JoyApp (follow same pattern):**

```python
# In app.py JoyApp class:
@property
def projects(self) -> list[Project]:
    """Public read access to project list."""
    return self._projects

@property
def config(self) -> Config:
    """Public read access to configuration."""
    return self._config

@property
def current_worktrees(self) -> list[WorktreeInfo]:
    """Public read access to last-fetched worktree snapshot."""
    return self._current_worktrees
```

**New public methods on JoyApp (thin wrappers over existing private methods):**

Pattern: the existing `_save_projects_bg` (app.py lines 734-738) becomes:
```python
def save_projects(self) -> None:
    """Public: persist projects to TOML in background."""
    self._save_projects_bg()
```

Apply to all private methods accessed cross-boundary (from RESEARCH.md inventory):
- `_save_projects_bg()` -> `save_projects()`
- `_close_tab_bg(tab_id)` -> `close_tab(tab_id)`
- `_append_to_archive_bg(archived)` -> `append_to_archive(archived)`
- `_remove_from_archive_bg(archived)` -> `remove_from_archive(archived)`
- `_load_terminal()` -> `refresh_terminal()`
- `_start_add_object_loop(project)` -> `start_add_object_loop(project)`
- `_update_badges()` -> `update_badges()`

**Cross-boundary access replacement in app.py** (lines to change):

app.py line 371-372 -- accessing `project_list._cursor` and `project_list._rows`:
```python
# BEFORE (app.py lines 371-372):
if project_list._cursor >= 0 and project_list._cursor < len(project_list._rows):
    current = project_list._rows[project_list._cursor].project

# AFTER:
current = project_list.current_project
if current is not None:
```

app.py line 676 -- accessing `detail._project`:
```python
# BEFORE (app.py line 676):
project = detail._project

# AFTER:
project = detail.current_project
```

app.py lines 680-683 -- accessing `detail._rows`:
```python
# BEFORE (app.py lines 680-683):
defaults: list[ObjectItem] = [
    row.item for row in detail._rows
    if row.item.open_by_default
]

# AFTER:
defaults = detail.default_items
```

app.py line 810 -- accessing `detail._project`:
```python
# BEFORE (app.py line 810):
project = detail._project

# AFTER:
project = detail.current_project
```

app.py lines 912-915 -- accessing `pane._cursor` and `pane._rows`:
```python
# BEFORE (app.py lines 912-915):
if pane._cursor < 0 or not pane._rows or pane._cursor >= len(pane._rows):
    self.notify("No worktree selected", markup=False)
    return
self._open_worktree_path(pane._rows[pane._cursor].path)

# AFTER:
wt = pane.highlighted_worktree
if wt is None:
    self.notify("No worktree selected", markup=False)
    return
self._open_worktree_path(wt.path)
```

app.py lines 406-407 -- accessing `self._rel_index._project_for_wt_path.keys()`:
```python
# BEFORE (app.py lines 406-407):
linked_paths: set[str] = set(self._rel_index._project_for_wt_path.keys())
linked_branches: set[tuple[str, str]] = set(self._rel_index._project_for_wt_branch.keys())

# AFTER:
linked_paths = self._rel_index.linked_worktree_paths
linked_branches = self._rel_index.linked_worktree_branches
```

---

### `src/joy/resolver.py` (service, transform) -- MODIFIED

**Analog:** Self (add public properties)

**Existing property pattern** -- resolver.py has public methods like `worktrees_for` (line 31-33) and `project_for_worktree` (line 39-45). New properties follow the same style:

```python
# resolver.py RelationshipIndex class:
# Existing public method (line 31-33):
def worktrees_for(self, project: Project) -> list[WorktreeInfo]:
    """Return all worktrees matched to the given project."""
    return self._wt_for_project.get(project.name, [])

# NEW public properties (same style):
@property
def linked_worktree_paths(self) -> set[str]:
    """Set of worktree paths linked to any project."""
    return set(self._project_for_wt_path.keys())

@property
def linked_worktree_branches(self) -> set[tuple[str, str]]:
    """Set of (repo_name, branch) tuples linked to any project."""
    return set(self._project_for_wt_branch.keys())
```

---

### `src/joy/widgets/project_detail.py` (component, request-response) -- MODIFIED

**Analog:** `src/joy/widgets/worktree_pane.py` (same cursor/_rows/highlight pattern)

**Existing `highlighted_object` property** (project_detail.py lines 416-421):
```python
@property
def highlighted_object(self) -> ObjectItem | None:
    """Return the currently highlighted ObjectItem, or None if no cursor."""
    if self._project and 0 <= self._cursor < len(self._rows):
        return self._rows[self._cursor].item
    return None
```

**New facade properties (same style):**

```python
@property
def current_project(self) -> Project | None:
    """The currently displayed project."""
    return self._project

@property
def default_items(self) -> list[ObjectItem]:
    """All items with open_by_default=True from current rows."""
    return [row.item for row in self._rows if row.item.open_by_default]
```

**New `clear()` method** -- pattern extracted from project_list.py lines 607-612 where app.py currently reaches in to clear the detail pane:
```python
# BEFORE (project_list.py lines 607-612 -- cross-boundary violation):
detail._project = None
detail._rows = []
detail._cursor = -1
scroll = detail.query_one("#detail-scroll")
scroll.remove_children()

# AFTER (new public method on ProjectDetail):
def clear(self) -> None:
    """Clear the detail pane (no project selected)."""
    self._project = None
    self._rows = []
    self._cursor = -1
    scroll = self.query_one("#detail-scroll")
    scroll.remove_children()
```

**Widget `self.app._config` access replacement** (project_detail.py line 143):
```python
# BEFORE (project_detail.py line 143):
default_kinds: list[str] = getattr(getattr(self, "app", None), "_config", None) and self.app._config.default_open_kinds or []

# AFTER:
default_kinds: list[str] = getattr(getattr(self, "app", None), "config", None) and self.app.config.default_open_kinds or []
```

**Widget `self.app._config` in _do_open** (project_detail.py lines 289, 291):
```python
# BEFORE (project_detail.py lines 289, 291):
open_object(item=item, config=self.app._config)
_success_message(item, self.app._config),

# AFTER:
open_object(item=item, config=self.app.config)
_success_message(item, self.app.config),
```

**Widget `self.app._start_add_object_loop` call** (project_detail.py line 314):
```python
# BEFORE:
self.app._start_add_object_loop(self._project)

# AFTER:
self.app.start_add_object_loop(self._project)
```

**Widget `self.app._projects` in _save_toggle** (project_detail.py line 414):
```python
# BEFORE:
save_projects(self.app._projects)

# AFTER:
save_projects(self.app.projects)
```

---

### `src/joy/widgets/project_list.py` (component, request-response) -- MODIFIED

**Analog:** `src/joy/widgets/worktree_pane.py` (same cursor/_rows/highlight pattern)

**New `current_project` property** (follow worktree_pane highlighted_worktree pattern):
```python
@property
def current_project(self) -> Project | None:
    """The currently highlighted project."""
    if 0 <= self._cursor < len(self._rows):
        return self._rows[self._cursor].project
    return None
```

**Private app access replacements -- all instances (from RESEARCH.md inventory):**

Line 500 -- `self.app._update_badges()`:
```python
# BEFORE:
self.app._update_badges()
# AFTER:
self.app.update_badges()
```

Lines 544, 549, 587, 643, 686, 742, 745, 816 -- `self.app._projects`:
```python
# BEFORE:
self.app._projects
# AFTER:
self.app.projects
```

Lines 548, 592, 639, 691, 743, 815 -- `self.app._save_projects_bg()`:
```python
# BEFORE:
self.app._save_projects_bg()
# AFTER:
self.app.save_projects()
```

Lines 586, 669 -- `self.app._close_tab_bg(...)`:
```python
# BEFORE:
self.app._close_tab_bg(project.iterm_tab_id)
# AFTER:
self.app.close_tab(project.iterm_tab_id)
```

Line 698 -- `self.app._append_to_archive_bg(archived)`:
```python
# BEFORE:
self.app._append_to_archive_bg(archived)
# AFTER:
self.app.append_to_archive(archived)
```

Line 734 -- `self.app._current_worktrees`:
```python
# BEFORE:
self.app._current_worktrees
# AFTER:
self.app.current_worktrees
```

Line 744 -- `self.app._remove_from_archive_bg(result)`:
```python
# BEFORE:
self.app._remove_from_archive_bg(result)
# AFTER:
self.app.remove_from_archive(result)
```

Lines 607-612 -- direct private access into ProjectDetail:
```python
# BEFORE:
detail._project = None
detail._rows = []
detail._cursor = -1
scroll = detail.query_one("#detail-scroll")
scroll.remove_children()
# AFTER:
detail.clear()
```

---

### `src/joy/widgets/worktree_pane.py` (component, request-response) -- MODIFIED

**Analog:** Self (add property)

**New `highlighted_worktree` property** -- follows the same pattern as `highlighted_object` in project_detail.py (lines 416-421):
```python
@property
def highlighted_worktree(self) -> WorktreeInfo | None:
    """The currently highlighted worktree, or None."""
    if 0 <= self._cursor < len(self._rows):
        row = self._rows[self._cursor]
        return WorktreeInfo(repo_name=row.repo_name, branch=row.branch, path=row.path)
    return None
```

**Existing public API that stays unchanged:**
- `sync_to(repo_name, branch)` (line 428-444) -- already public
- `clear_selection()` (line 446-450) -- already public

---

### `src/joy/widgets/terminal_pane.py` (component, request-response) -- MODIFIED

**Analog:** `src/joy/widgets/worktree_pane.py` (identical cursor/_rows pattern)

**New `highlighted_session` property** -- follows same pattern as worktree_pane:
```python
@property
def highlighted_session(self) -> str | None:
    """The session_name of the currently highlighted session, or None."""
    if 0 <= self._cursor < len(self._rows):
        return self._rows[self._cursor].session_name
    return None
```

**Private app access replacements:**

Lines 465, 493, 524 -- `self.app._load_terminal()`:
```python
# BEFORE:
self.app._load_terminal()
# AFTER:
self.app.refresh_terminal()
```

**Existing public API that stays unchanged:**
- `sync_to(session_name)` (line 388-403) -- already public
- `clear_selection()` (line 405-409) -- already public

---

### `tests/test_ports.py` (test, unit) -- NEW FILE

**Analog:** `tests/test_resolver.py`

**Test file structure** (test_resolver.py lines 1-19):
```python
"""Tests for the cross-pane relationship resolver (Phase 14, Plan 01).

All tests are pure Python -- no TUI, no I/O, no mocking needed.
"""
from __future__ import annotations

import pytest

from joy.models import ObjectItem, PresetKind, Project, Repo, TerminalSession, WorktreeInfo
from joy.resolver import RelationshipIndex, compute_relationships


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def make_project(name: str, objects=None, repo=None, iterm_tab_id=None) -> Project:
    return Project(name=name, objects=objects or [], repo=repo, iterm_tab_id=iterm_tab_id)
```

For test_ports.py, the equivalent structure:
```python
"""Tests for Protocol contracts (Phase 18).

All tests are pure Python -- no TUI, no I/O, no mocking needed.
Validates Protocol classes exist with correct signatures and
@runtime_checkable isinstance() checks pass for structural conformance.
"""
from __future__ import annotations

from joy.ports import StoragePort, GitDataPort, TerminalPort, OpenerPort, SyncablePane
```

**Test pattern -- isinstance check for @runtime_checkable Protocol** (pure Python, no mocking):
```python
def test_storage_port_structural_conformance():
    """Verify that a class with matching methods satisfies StoragePort."""
    class FakeStorage:
        def load_projects(self) -> list: return []
        def save_projects(self, projects) -> None: pass
        # ... all methods
    assert isinstance(FakeStorage(), StoragePort)
```

**Section separator pattern** (test_resolver.py lines 36-39):
```python
# ---------------------------------------------------------------------------
# Test 1: worktree matched by WORKTREE path object
# ---------------------------------------------------------------------------
```

---

## Shared Patterns

### `from __future__ import annotations`
**Source:** Every file in `src/joy/` (line 1-2 pattern)
**Apply to:** All new and modified files
```python
from __future__ import annotations
```

### Property-based facade accessor
**Source:** `src/joy/widgets/project_detail.py` lines 416-421
**Apply to:** All widget facade properties (current_project, highlighted_worktree, highlighted_session, default_items)
```python
@property
def highlighted_object(self) -> ObjectItem | None:
    """Return the currently highlighted ObjectItem, or None if no cursor."""
    if self._project and 0 <= self._cursor < len(self._rows):
        return self._rows[self._cursor].item
    return None
```

### Public method wrapping private method
**Source:** Pattern derived from existing `_save_projects_bg` (app.py line 734-738) being called by widgets
**Apply to:** All JoyApp public facade methods
```python
def save_projects(self) -> None:
    """Public: persist projects to TOML in background."""
    self._save_projects_bg()
```

### Lazy import pattern
**Source:** `src/joy/app.py` (throughout, e.g., line 142)
**Apply to:** Any import in app.py that is inside a method body stays inside; no changes to import location.
```python
from joy.store import load_config, load_projects, load_repos  # noqa: PLC0415 -- lazy import per CP-2
```

### Test section separator
**Source:** `tests/test_resolver.py` (throughout)
**Apply to:** test_ports.py
```python
# ---------------------------------------------------------------------------
# Test N: description
# ---------------------------------------------------------------------------
```

### Cursor/rows guard pattern
**Source:** `src/joy/widgets/worktree_pane.py` line 428-444, `src/joy/widgets/terminal_pane.py` line 388-403
**Apply to:** All `highlighted_*` properties
```python
if 0 <= self._cursor < len(self._rows):
    # ... access self._rows[self._cursor]
    return <value>
return None
```

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| (none) | -- | -- | All files have close analogs in the existing codebase |

Every file to be created or modified has a direct pattern source within the joy codebase. No external reference patterns are needed.

## Metadata

**Analog search scope:** `src/joy/`, `src/joy/widgets/`, `tests/`
**Files scanned:** 24 source files + 27 test files
**Pattern extraction date:** 2026-05-07
