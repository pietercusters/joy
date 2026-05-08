# Phase 18: Contracts & Facades - Research

**Researched:** 2026-05-07
**Domain:** Python typing.Protocol contracts, widget facade patterns, dependency inversion
**Confidence:** HIGH

## Summary

Phase 18 introduces explicit interface contracts between joy's widget layer and the app composition root. Currently, `app.py` reaches into widget private attributes (`_project`, `_rows`, `_cursor`) and widgets reach into `app._projects`, `app._config`, `app._save_projects_bg()`, etc. This creates tight coupling that makes future extraction of services (Phase 19) difficult.

The phase has two primary workstreams: (1) defining `typing.Protocol` classes in a new `ports.py` module for backend service boundaries (StoragePort, GitDataPort, TerminalPort, OpenerPort), and (2) adding public facade properties/methods to each widget so `app.py` never accesses private attributes across module boundaries. The SyncablePane Protocol formalizes the existing `sync_to()` / `clear_selection()` contract that WorktreePane and TerminalPane already satisfy structurally.

**Primary recommendation:** Work bottom-up -- first add public facade properties to widgets (pure additions, no breakage), then replace all private-attribute accesses in app.py, then define Protocol classes in ports.py. This order ensures every intermediate commit passes all tests.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Protocol definitions (ports.py) | Shared/contracts layer | -- | Pure type definitions with no runtime behavior; imported by both app.py and future services |
| Widget facade properties | Frontend (Textual widgets) | -- | Properties live on widget classes; they expose internal state through public API |
| Private-access elimination in app.py | App composition root | -- | app.py is the only consumer of widget facades; it wires dependencies |
| SyncablePane Protocol | Shared/contracts layer | Frontend (widgets) | Protocol defined in ports.py; structurally satisfied by WorktreePane + TerminalPane |
| RelationshipIndex public API | Backend (resolver.py) | -- | RelationshipIndex needs public methods for linked_paths/linked_branches (currently accessed via private fields) |

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CNTR-01 | Protocol definitions exist in ports.py for StoragePort, GitDataPort, TerminalPort, OpenerPort | Section "Architecture Patterns > Pattern 1" provides exact method signatures derived from codebase audit |
| CNTR-02 | SyncablePane Protocol defines sync_to() and clear_selection() contracts | Section "Architecture Patterns > Pattern 2" documents the existing structural conformance |
| CNTR-03 | All widget private-field access from app.py replaced with public facade properties | Section "Cross-Boundary Violation Inventory" catalogs every violation with replacement strategy |
| CNTR-04 | ProjectDetail exposes clear(), show_project(), default_items via public methods | Section "Widget Facade Requirements > ProjectDetail" lists exact signatures needed |
| CNTR-05 | WorktreePane and TerminalPane expose highlighted_worktree/highlighted_session as public properties | Section "Widget Facade Requirements > WorktreePane / TerminalPane" shows property design |
| ARCH-01 | No widget imports Protocol adapter directly -- dependency flows through app.py | Section "Architecture Patterns > Pattern 3" explains composition root wiring |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| typing (stdlib) | Python 3.11+ | Protocol, runtime_checkable | Built-in structural subtyping; no dependencies needed [VERIFIED: Python stdlib docs] |
| dataclasses (stdlib) | Python 3.11+ | Data model classes | Already used throughout joy for models.py [VERIFIED: codebase inspection] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| typing_extensions | -- | NOT needed | Python 3.11+ includes all needed Protocol features in stdlib [VERIFIED: Python docs] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| typing.Protocol | abc.ABC | ABC requires explicit inheritance (nominal subtyping); Protocol provides structural subtyping which is more Pythonic for duck-typing and explicitly OUT OF SCOPE per REQUIREMENTS.md |
| Manual Protocol definitions | dependency-injector framework | Explicitly OUT OF SCOPE per REQUIREMENTS.md: "Manual constructor injection sufficient at 4-5 ports" |

**Installation:** No new dependencies needed. All required functionality is in Python 3.11+ stdlib.

## Architecture Patterns

### System Architecture Diagram

```
                     Current (Before Phase 18)
                     ========================

    app.py (JoyApp)
      |
      |-- reads --> widget._project, widget._rows, widget._cursor
      |-- calls --> widget.set_project(), widget.sync_to()
      |
      |-- widgets reach back:
      |     widget --> self.app._projects
      |     widget --> self.app._config
      |     widget --> self.app._save_projects_bg()
      |     widget --> self.app._load_terminal()
      |
      |-- directly calls --> store.load_projects(), store.save_projects()
      |-- directly calls --> worktrees.discover_worktrees()
      |-- directly calls --> terminal_sessions.fetch_sessions()
      |-- directly calls --> operations.open_object()


                     Target (After Phase 18)
                     =======================

    ports.py (Protocol definitions)
      |-- StoragePort: load_projects, save_projects, load_config, ...
      |-- GitDataPort: discover_worktrees, fetch_mr_data
      |-- TerminalPort: fetch_sessions, create_tab, activate_session, ...
      |-- OpenerPort: open_object
      |-- SyncablePane: sync_to, clear_selection
      |
    app.py (JoyApp -- composition root)
      |
      |-- reads --> widget.current_project, widget.highlighted_item, ...
      |-- calls --> widget.show_project(), widget.clear(), widget.default_items
      |-- calls --> syncable_pane.sync_to(), syncable_pane.clear_selection()
      |
      |-- widgets use public methods only:
      |     widget --> self.app.projects (property)
      |     widget --> self.app.config (property)
      |     widget --> self.app.save_projects()
      |     widget --> self.app.refresh_terminal()
      |
      |-- app.py wires concrete adapters to Protocol ports (Phase 19)
      |
    Widgets NEVER import ports.py adapters directly (ARCH-01)
```

### Recommended Project Structure
```
src/joy/
    ports.py          # NEW: Protocol definitions (StoragePort, GitDataPort, etc.)
    app.py            # MODIFIED: public properties/methods replace private access
    models.py         # UNCHANGED
    store.py          # UNCHANGED (becomes concrete adapter in Phase 19)
    resolver.py       # MODIFIED: public methods for linked_paths/linked_branches
    widgets/
        project_detail.py  # MODIFIED: add facade properties
        project_list.py    # MODIFIED: add facade properties, use app public API
        worktree_pane.py   # MODIFIED: add highlighted_worktree property
        terminal_pane.py   # MODIFIED: add highlighted_session property
        mr_pane.py         # UNCHANGED (no cross-boundary violations)
```

### Pattern 1: Protocol Definitions in ports.py

**What:** Define typing.Protocol classes for backend service boundaries
**When to use:** When multiple concrete implementations might satisfy the same contract (e.g., real store vs. fake store in tests)
**Example:**
```python
# Source: Python 3.11+ stdlib typing.Protocol
# [VERIFIED: Python docs https://docs.python.org/3/library/typing.html#typing.Protocol]
from __future__ import annotations

from typing import Protocol, runtime_checkable

from joy.models import (
    ArchivedProject, Config, ObjectItem, Project, Repo,
    TerminalSession, WorktreeInfo,
)


@runtime_checkable
class StoragePort(Protocol):
    """Contract for project/config persistence."""

    def load_projects(self) -> list[Project]: ...
    def save_projects(self, projects: list[Project]) -> None: ...
    def load_config(self) -> Config: ...
    def save_config(self, config: Config) -> None: ...
    def load_repos(self) -> list[Repo]: ...
    def save_repos(self, repos: list[Repo]) -> None: ...
    def load_archived_projects(self) -> list[ArchivedProject]: ...
    def save_archived_projects(self, projects: list[ArchivedProject]) -> None: ...


@runtime_checkable
class GitDataPort(Protocol):
    """Contract for git data discovery."""

    def discover_worktrees(self, repos: list[Repo], branch_filter: list[str]) -> list[WorktreeInfo]: ...


@runtime_checkable
class TerminalPort(Protocol):
    """Contract for terminal session management."""

    def fetch_sessions(self) -> tuple[list[TerminalSession], set[str]] | None: ...
    def create_tab(self, name: str) -> str | None: ...
    def activate_session(self, session_id: str) -> None: ...
    def close_session(self, session_id: str, *, force: bool) -> bool: ...
    def close_tab(self, tab_id: str, *, force: bool) -> None: ...
    def create_session(self, name: str) -> str | None: ...
    def rename_session(self, session_id: str, new_name: str) -> bool: ...


@runtime_checkable
class OpenerPort(Protocol):
    """Contract for opening objects (URLs, files, etc.)."""

    def open_object(self, *, item: ObjectItem, config: Config) -> None: ...
```

**Key design decisions:**
- `@runtime_checkable` enables `isinstance()` checks in tests for contract verification [VERIFIED: Python docs]
- Methods use the same signatures as current module-level functions for easy Phase 19 adaptation
- Protocols import from `joy.models` only (no circular dependencies)
- StoragePort wraps all `joy.store` functions; GitDataPort wraps `joy.worktrees` + `joy.mr_status`
- TerminalPort wraps all `joy.terminal_sessions` functions

### Pattern 2: SyncablePane Protocol

**What:** Formalize the sync_to/clear_selection contract already structurally satisfied by WorktreePane and TerminalPane
**When to use:** Any pane that participates in cross-pane sync coordination
**Example:**
```python
# Source: Codebase analysis of WorktreePane.sync_to/clear_selection + TerminalPane equivalents
# [VERIFIED: codebase inspection]
class SyncablePane(Protocol):
    """Contract for panes that support cross-pane sync."""

    def sync_to(self, *args: str) -> bool:
        """Move cursor to matching item. Returns True if found."""
        ...

    def clear_selection(self) -> None:
        """Reset cursor to -1, remove all highlights."""
        ...
```

**Note:** WorktreePane.sync_to takes `(repo_name, branch)` while TerminalPane.sync_to takes `(session_name)`. The Protocol uses `*args: str` to accommodate both signatures. Alternatively, keep the Protocol generic and use separate typed calls in the coordinator. The planner should decide which approach: (a) a single SyncablePane with `*args`, or (b) distinct WorktreeSyncable and TerminalSyncable protocols. Option (b) is more type-safe. [ASSUMED]

### Pattern 3: Composition Root (ARCH-01 enforcement)

**What:** app.py is the only module that knows about concrete implementations. Widgets get data pushed to them; they never import backend modules.
**When to use:** Always -- this is the architectural invariant for Phase 18+.
**Example:**
```python
# In app.py (the composition root):
class JoyApp(App):
    @property
    def projects(self) -> list[Project]:
        """Public read access to project list."""
        return self._projects

    @property
    def config(self) -> Config:
        """Public read access to configuration."""
        return self._config

    def save_projects(self) -> None:
        """Public method for widgets to trigger project persistence."""
        self._save_projects_bg()

    def refresh_terminal(self) -> None:
        """Public method for widgets to trigger terminal refresh."""
        self._load_terminal()

# In widget code (consumer):
# BEFORE: self.app._projects  (private access)
# AFTER:  self.app.projects   (public property)
```

### Anti-Patterns to Avoid
- **Widget reaching into app._private_attr:** The entire purpose of this phase is eliminating this pattern. Every `self.app._foo` in a widget must become `self.app.foo` (public).
- **Protocol classes with implementations:** ports.py should contain ONLY Protocol definitions, no concrete classes. Concrete adapters belong in their respective modules (store.py, worktrees.py, etc.) or in a future adapters.py (Phase 19).
- **Circular imports from ports.py:** ports.py imports only from models.py. Never import ports.py from models.py. app.py imports ports.py. Widgets do NOT import ports.py (ARCH-01).
- **Big-bang refactor:** Resist the urge to change all files in one commit. Each facade property addition and each private-access replacement should be independently testable.

## Cross-Boundary Violation Inventory

### app.py accessing widget private attributes

| Line(s) | Widget | Private Access | Replacement Strategy |
|---------|--------|---------------|---------------------|
| 371-372 | ProjectList | `project_list._cursor`, `project_list._rows` | Add `ProjectList.current_project` property that returns the highlighted Project or None |
| 676 | ProjectDetail | `detail._project` | Add `ProjectDetail.current_project` property |
| 681 | ProjectDetail | `detail._rows` | Add `ProjectDetail.default_items` property returning list of open_by_default ObjectItems |
| 810 | ProjectDetail | `detail._project` | Reuse `ProjectDetail.current_project` property |
| 912-915 | WorktreePane | `pane._cursor`, `pane._rows` | Add `WorktreePane.highlighted_worktree_path` property returning str or None |

### app.py accessing RelationshipIndex private attributes

| Line(s) | Module | Private Access | Replacement Strategy |
|---------|--------|---------------|---------------------|
| 406 | resolver.py | `self._rel_index._project_for_wt_path.keys()` | Add `RelationshipIndex.linked_worktree_paths` property |
| 407 | resolver.py | `self._rel_index._project_for_wt_branch.keys()` | Add `RelationshipIndex.linked_worktree_branches` property |

### Widgets accessing app private attributes

| File | Line(s) | Private Access | Replacement Strategy |
|------|---------|---------------|---------------------|
| project_detail.py | 143 | `self.app._config.default_open_kinds` | Add `JoyApp.config` public property |
| project_detail.py | 289, 291 | `self.app._config` | Reuse `JoyApp.config` property |
| project_detail.py | 314 | `self.app._start_add_object_loop()` | Make this a public method: `JoyApp.start_add_object_loop()` |
| project_detail.py | 414 | `self.app._projects` | Add `JoyApp.projects` public property |
| project_list.py | 500 | `self.app._update_badges()` | Make public: `JoyApp.update_badges()` |
| project_list.py | 544, 549, 587, 643, 686, 742, 745, 816 | `self.app._projects` | Reuse `JoyApp.projects` property |
| project_list.py | 548, 592, 639, 691, 743, 815 | `self.app._save_projects_bg()` | Make public: `JoyApp.save_projects()` |
| project_list.py | 586, 669 | `self.app._close_tab_bg()` | Make public: `JoyApp.close_tab()` |
| project_list.py | 698 | `self.app._append_to_archive_bg()` | Make public: `JoyApp.append_to_archive()` |
| project_list.py | 734 | `self.app._current_worktrees` | Add `JoyApp.current_worktrees` property |
| project_list.py | 744 | `self.app._remove_from_archive_bg()` | Make public: `JoyApp.remove_from_archive()` |
| project_list.py | 608-610 | `detail._project`, `detail._rows`, `detail._cursor` | Add `ProjectDetail.clear()` public method |
| terminal_pane.py | 465, 493, 524 | `self.app._load_terminal()` | Make public: `JoyApp.refresh_terminal()` |

## Widget Facade Requirements

### ProjectDetail

```python
# New public properties/methods needed on ProjectDetail:
class ProjectDetail(Widget):
    @property
    def current_project(self) -> Project | None:
        """The currently displayed project."""
        return self._project

    @property
    def highlighted_object(self) -> ObjectItem | None:
        """Already exists -- no change needed."""
        ...

    @property
    def default_items(self) -> list[ObjectItem]:
        """All items with open_by_default=True from current rows."""
        return [row.item for row in self._rows if row.item.open_by_default]

    def clear(self) -> None:
        """Clear the detail pane (no project selected)."""
        self._project = None
        self._rows = []
        self._cursor = -1
        scroll = self.query_one("#detail-scroll")
        scroll.remove_children()

    # show_project() -- alias for existing set_project() or rename
    # set_project() already serves this purpose; CNTR-04 may just
    # mean ensuring it is the documented public API.
```

### ProjectList

```python
class ProjectList(Widget):
    @property
    def current_project(self) -> Project | None:
        """The currently highlighted project."""
        if 0 <= self._cursor < len(self._rows):
            return self._rows[self._cursor].project
        return None

    @property
    def cursor_index(self) -> int:
        """Current cursor position."""
        return self._cursor
```

### WorktreePane

```python
class WorktreePane(Widget):
    @property
    def highlighted_worktree(self) -> WorktreeInfo | None:
        """The currently highlighted worktree, or None."""
        if 0 <= self._cursor < len(self._rows):
            row = self._rows[self._cursor]
            return WorktreeInfo(repo_name=row.repo_name, branch=row.branch, path=row.path)
        return None

    # sync_to() and clear_selection() already exist as public methods.
```

### TerminalPane

```python
class TerminalPane(Widget):
    @property
    def highlighted_session(self) -> str | None:
        """The session_name of the currently highlighted session, or None."""
        if 0 <= self._cursor < len(self._rows):
            return self._rows[self._cursor].session_name
        return None

    # sync_to() and clear_selection() already exist as public methods.
```

### RelationshipIndex

```python
class RelationshipIndex:
    @property
    def linked_worktree_paths(self) -> set[str]:
        """Set of worktree paths linked to any project."""
        return set(self._project_for_wt_path.keys())

    @property
    def linked_worktree_branches(self) -> set[tuple[str, str]]:
        """Set of (repo_name, branch) tuples linked to any project."""
        return set(self._project_for_wt_branch.keys())
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Interface contracts | Custom ABC hierarchy | typing.Protocol | Structural subtyping is more Pythonic; no inheritance required; explicitly recommended in REQUIREMENTS.md |
| Dependency injection | DI framework | Manual constructor injection | REQUIREMENTS.md explicitly rules out DI frameworks: "Manual constructor injection sufficient at 4-5 ports" |
| Runtime contract checking | Custom isinstance() wrappers | @runtime_checkable Protocol | Built-in Python feature since 3.8; checks method existence at runtime |

**Key insight:** This phase is about making existing implicit contracts explicit, not about adding new runtime behavior. The Protocol definitions are primarily for type-checker verification and documentation; the actual runtime behavior already works correctly.

## Common Pitfalls

### Pitfall 1: Breaking tests with property renames
**What goes wrong:** Renaming `_project` to a property changes attribute access semantics; test code that patches or sets `widget._project = X` will break.
**Why it happens:** Properties are read-only by default; tests that directly set private attributes need to use the public setter method instead.
**How to avoid:** Keep private attributes as backing stores; add properties as NEW read-only accessors. The private attribute remains for internal use. `_project` stays, `current_project` property reads it.
**Warning signs:** Tests patching `_project` directly (check conftest.py and test files).

### Pitfall 2: Protocol signature mismatch with SyncablePane
**What goes wrong:** WorktreePane.sync_to(repo_name, branch) and TerminalPane.sync_to(session_name) have different arity, making a single Protocol definition tricky.
**Why it happens:** The sync contract evolved per-pane with different data shapes.
**How to avoid:** Either (a) use `*args: str` in the Protocol, (b) define separate Protocols (WorktreeSyncable, TerminalSyncable), or (c) accept that the PaneCoordinator (Phase 19) will call these with specific knowledge of each pane type. Option (c) is pragmatic -- the Protocol documents the "shape" of sync, and the coordinator knows the specifics.
**Warning signs:** mypy errors about incompatible overrides.

### Pitfall 3: Circular imports from ports.py
**What goes wrong:** ports.py imports from models.py; if models.py later imports from ports.py, circular import occurs.
**Why it happens:** Natural tendency to co-locate type annotations with data models.
**How to avoid:** ports.py imports ONLY from models.py. models.py NEVER imports from ports.py. Widgets NEVER import ports.py (ARCH-01). Only app.py and future service modules import ports.py.
**Warning signs:** ImportError during startup.

### Pitfall 4: Incomplete facade coverage
**What goes wrong:** Some private access paths are missed; app.py still reaches into widget internals after the phase is "complete."
**Why it happens:** Private accesses are scattered across 30+ locations; easy to miss edge cases.
**How to avoid:** Use the Cross-Boundary Violation Inventory above as a checklist. Run `grep -rn 'detail\._\|pane\._\|list\._' src/joy/app.py` and `grep -rn 'self\.app\._' src/joy/widgets/` after each plan to verify zero violations remain.
**Warning signs:** grep returning results for private cross-boundary access patterns.

### Pitfall 5: Over-engineering the Protocol hierarchy
**What goes wrong:** Creating too many fine-grained Protocols or adding methods that aren't needed yet.
**Why it happens:** Temptation to design for all possible future uses.
**How to avoid:** Each Protocol method must correspond to a real call site in the current codebase. If no code calls it today, don't add it. Phase 19 (Service Extraction) will add methods as needed.
**Warning signs:** Protocol methods with no callers.

### Pitfall 6: ProjectList._rebuild calling self.app._update_badges()
**What goes wrong:** ProjectList line 500 calls `self.app._update_badges()` -- this is a reverse dependency where a widget triggers an app-level method. Simply renaming to public doesn't fix the architectural issue.
**Why it happens:** After rebuilding rows, badges need to be reapplied. The widget needs to signal the app that rows changed.
**How to avoid:** Make `update_badges()` a public method on JoyApp. This is acceptable in the composition root pattern -- the widget calls a public app method that orchestrates data flow. The alternative (message posting) is over-engineering for this use case.
**Warning signs:** Bidirectional dependency between widget and app.

## Code Examples

### Defining a Protocol with runtime_checkable

```python
# Source: Python 3.11+ stdlib
# [VERIFIED: https://docs.python.org/3/library/typing.html#typing.Protocol]
from typing import Protocol, runtime_checkable

@runtime_checkable
class StoragePort(Protocol):
    def load_projects(self) -> list[Project]: ...
    def save_projects(self, projects: list[Project]) -> None: ...

# Structural subtyping -- no inheritance needed:
class TomlStorage:  # does NOT inherit StoragePort
    def load_projects(self) -> list[Project]:
        return load_projects()  # delegates to store module function

    def save_projects(self, projects: list[Project]) -> None:
        save_projects(projects)  # delegates to store module function

# Type checker accepts this -- TomlStorage structurally satisfies StoragePort:
storage: StoragePort = TomlStorage()

# Runtime check also works:
assert isinstance(TomlStorage(), StoragePort)
```

### Adding a facade property to a widget

```python
# Source: Codebase pattern analysis
# [VERIFIED: codebase inspection]

# BEFORE (app.py accesses private attribute):
project = detail._project  # line 676

# AFTER (widget exposes public property):
# In project_detail.py:
@property
def current_project(self) -> Project | None:
    return self._project

# In app.py:
project = detail.current_project  # clean public access
```

### Making app methods public for widget consumption

```python
# Source: Codebase pattern analysis
# [VERIFIED: codebase inspection]

# BEFORE (widget calls private app method):
self.app._save_projects_bg()  # in project_list.py

# AFTER (app exposes public method):
# In app.py:
def save_projects(self) -> None:
    """Public: persist projects to TOML in background."""
    self._save_projects_bg()

# In project_list.py:
self.app.save_projects()  # clean public call
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| abc.ABC for interfaces | typing.Protocol | Python 3.8+ (PEP 544) | Structural subtyping, no inheritance needed |
| @runtime_checkable limitations | Full Protocol support | Python 3.12 improved | Better error messages, faster isinstance checks |
| Manual duck typing | Protocol + type checkers | 2020+ | mypy/pyright verify structural conformance at check time |

**Deprecated/outdated:**
- abc.ABC for service boundaries: Still works but Protocol is preferred for structural (duck-type) interfaces in modern Python. REQUIREMENTS.md explicitly excludes ABC.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | SyncablePane should use `*args: str` or separate protocols for different sync_to signatures | Architecture Patterns > Pattern 2 | Planner may need to decide between type safety vs. simplicity; low risk either way |
| A2 | `show_project()` in CNTR-04 refers to the existing `set_project()` method, not a new method | Widget Facade Requirements > ProjectDetail | If it means a renamed method, one more refactoring step needed |
| A3 | Phase 18 only defines Protocols but does NOT create concrete adapter classes | Architecture Patterns > Pattern 1 | If concrete adapters are needed now, scope increases; REQUIREMENTS.md says Phase 19 does extraction |

## Open Questions

1. **SyncablePane signature variance**
   - What we know: WorktreePane.sync_to(repo_name, branch) and TerminalPane.sync_to(session_name) have different signatures
   - What's unclear: Whether a single Protocol can cleanly represent both, or if separate protocols are better
   - Recommendation: Use separate protocols (WorktreeSyncable, TerminalSyncable) or accept that PaneCoordinator (Phase 19) calls each pane with specific knowledge. The planner should pick the pragmatic option.

2. **JoyApp public API method naming**
   - What we know: Private methods like `_save_projects_bg`, `_close_tab_bg` need public wrappers
   - What's unclear: Whether to keep bg-suffixed names public or use cleaner names
   - Recommendation: Drop the `_bg` suffix for public API. `save_projects()` is clearer than `save_projects_bg()`. The background threading is an implementation detail.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0+ with pytest-asyncio |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/ -x -q --no-header -m "not slow and not macos_integration"` |
| Full suite command | `uv run pytest tests/ -q --no-header -m "not slow and not macos_integration"` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CNTR-01 | ports.py Protocol classes exist with correct method signatures | unit | `uv run pytest tests/test_ports.py -x` | No -- Wave 0 |
| CNTR-02 | SyncablePane Protocol structurally satisfied by WorktreePane/TerminalPane | unit (isinstance check) | `uv run pytest tests/test_ports.py::test_syncable_pane -x` | No -- Wave 0 |
| CNTR-03 | No private-field cross-access in app.py | grep audit | `grep -rn 'detail\._\|pane\._' src/joy/app.py` returns 0 | manual |
| CNTR-04 | ProjectDetail public facade methods work | unit | `uv run pytest tests/test_project_detail_facade.py -x` | No -- Wave 0 |
| CNTR-05 | highlighted_worktree/highlighted_session properties work | unit | `uv run pytest tests/test_pane_facades.py -x` | No -- Wave 0 |
| ARCH-01 | No widget imports Protocol adapters | grep audit | `grep -rn 'from joy.ports\|import ports' src/joy/widgets/` returns 0 | manual |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -x -q --no-header -m "not slow and not macos_integration"`
- **Per wave merge:** `uv run pytest tests/ -q --no-header -m "not slow and not macos_integration"`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_ports.py` -- covers CNTR-01, CNTR-02 (Protocol existence and structural conformance)
- [ ] `tests/test_project_detail_facade.py` -- covers CNTR-04 (current_project, default_items, clear)
- [ ] `tests/test_pane_facades.py` -- covers CNTR-05 (highlighted_worktree, highlighted_session)

## Sources

### Primary (HIGH confidence)
- Python typing.Protocol docs: https://docs.python.org/3/library/typing.html#typing.Protocol -- Protocol definition, @runtime_checkable, structural subtyping
- Codebase inspection: `src/joy/app.py` (1058 LOC), `src/joy/widgets/` (6 widget files), `src/joy/resolver.py` -- all cross-boundary access patterns cataloged

### Secondary (MEDIUM confidence)
- PEP 544 (Protocols): https://peps.python.org/pep-0544/ -- authoritative specification for Protocol behavior

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- uses only Python stdlib typing.Protocol; no new dependencies
- Architecture: HIGH -- all violations cataloged from actual codebase grep; replacement strategies verified against existing method signatures
- Pitfalls: HIGH -- derived from direct codebase analysis (test patterns, import structure, method signatures)

**Research date:** 2026-05-07
**Valid until:** 2026-06-07 (stable -- stdlib typing.Protocol does not change between Python minor releases)
