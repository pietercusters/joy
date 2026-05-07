# Architecture Patterns: Ports & Adapters Refactoring for joy

**Domain:** Python TUI refactoring -- monolithic App to extracted services
**Researched:** 2026-05-07
**Confidence:** HIGH (based on direct codebase analysis + established Python patterns)

---

## 1. Current Architecture Analysis

### The Problem: app.py as God Object

`JoyApp` (1,058 LOC, 21 instance variables) currently serves as:
- **Widget orchestrator** -- coordinates 5 pane widgets via `query_one()` calls
- **Data loading coordinator** -- manages `@work(thread=True)` background tasks for worktrees, terminals, MR data
- **State container** -- holds `_projects`, `_repos`, `_config`, `_rel_index`, `_current_worktrees`, `_current_sessions`, etc.
- **Business logic host** -- MR auto-add propagation (37 lines), relationship computation, worktree link status
- **Cross-pane sync engine** -- `_sync_from_project`, `_sync_from_worktree`, `_sync_from_session` with `_is_syncing` guard

### Coupling Hotspots (Verified from Code)

| Hotspot | Location | Lines Affected | Severity |
|---------|----------|----------------|----------|
| Direct private field access on widgets | `app.py` lines 371-376, 606-617, 677-681, 912-915 | ~25 | CRITICAL |
| `detail._project`, `detail._rows`, `detail._cursor` manipulation | `app.py` line 677, `project_list.py` line 607-611 | 8 | CRITICAL |
| `pane._cursor` and `pane._rows` reads from app | `app.py` lines 371, 912 | 6 | HIGH |
| Widget to `self.app._config` reads | `project_detail.py` line 143, 289 | 4 | MEDIUM |
| Widget to `self.app._save_projects_bg()` calls | `project_list.py` lines 549, 593, 639, 700, 816 | 7 | MEDIUM |
| Widget to `self.app._projects` direct reads | `project_list.py` lines 545, 549, 816 | 5 | MEDIUM |
| Widget to `self.app._update_badges()` calls | `project_list.py` line 501 | 1 | MEDIUM |
| Business logic in `_propagate_changes` | `app.py` lines 349-377 | 28 | HIGH |
| Ready-flag coordination (`_worktrees_ready`, `_sessions_ready`) | `app.py` lines 96-97, 228-231, 258-261, 295-299 | 12 | MEDIUM |

### What Already Works Well (Do Not Touch)

These components are already cleanly separated and need no refactoring:

- **models.py** (214 LOC) -- Pure dataclasses, no I/O. Perfect domain layer.
- **store.py** (320 LOC) -- Clean TOML persistence with atomic writes. Already an adapter.
- **worktrees.py** (143 LOC) -- Pure functions for git worktree discovery.
- **resolver.py** (110 LOC) -- Pure-function RelationshipIndex computation. Already a domain service.
- **operations.py** (110 LOC) -- Type-dispatched subprocess operations. Already an adapter.
- **dispatch.py** (47 LOC) -- Data-driven dispatch table. Pure data.
- **mr_status.py** (652 LOC) -- MR/PR fetching. Already an adapter (I/O isolated).
- **terminal_sessions.py** (315 LOC) -- iTerm2 session fetching. Already an adapter.

---

## 2. Recommended Architecture

### Layer Diagram

```
+------------------------------------------------------------------+
|                        JoyApp (thin shell)                        |
|  compose(), on_mount(), action_*() delegates, message handlers    |
+------------------------------------------------------------------+
         |              |                    |
         v              v                    v
+----------------+  +------------------+  +-------------------+
| PaneCoordinator|  | DataOrchestrator |  | ProjectService    |
| (sync engine)  |  | (data loading)   |  | (CRUD operations) |
+----------------+  +------------------+  +-------------------+
         |              |                    |
         v              v                    v
+------------------------------------------------------------------+
|  Widget Facades: ProjectList, ProjectDetail, WorktreePane,       |
|  TerminalPane, MRPane -- public methods only, no private access  |
+------------------------------------------------------------------+
         |              |                    |
         v              v                    v
+------------------------------------------------------------------+
|  Pure Domain: models.py, resolver.py, dispatch.py                |
|  Adapters: store.py, operations.py, mr_status.py,               |
|            terminal_sessions.py, worktrees.py                    |
+------------------------------------------------------------------+
```

### New Components

#### 2a. PaneCoordinator (`src/joy/coordinator.py`)

**Responsibility:** All cross-pane sync logic, currently scattered across `_sync_from_project`, `_sync_from_worktree`, `_sync_from_session`, and the `_is_syncing` guard.

**Why extract:** The sync logic is pure orchestration with no I/O. It reads relationship data and tells panes where to move their cursors. Currently 120+ lines in app.py that can be tested without any TUI.

```python
"""Cross-pane sync coordinator. No Textual imports, no widgets."""
from __future__ import annotations

from typing import Protocol


class SyncableProjectList(Protocol):
    """Port: what the coordinator needs from the project list."""
    def sync_to(self, project_name: str) -> bool: ...
    def clear_selection(self) -> None: ...


class SyncableWorktreePane(Protocol):
    """Port: what the coordinator needs from the worktree pane."""
    def sync_to(self, repo_name: str, branch: str) -> bool: ...
    def clear_selection(self) -> None: ...


class SyncableTerminalPane(Protocol):
    """Port: what the coordinator needs from the terminal pane."""
    def sync_to(self, session_name: str) -> bool: ...
    def clear_selection(self) -> None: ...


class SyncableDetailPane(Protocol):
    """Port: what the coordinator needs from the detail pane."""
    def show_project(
        self, project, resolver_worktrees=None, resolver_terminals=None
    ) -> None: ...


class PaneCoordinator:
    """Drives cross-pane sync without knowing about Textual widgets."""

    def __init__(self) -> None:
        self._sync_enabled: bool = True
        self._is_syncing: bool = False

    @property
    def sync_enabled(self) -> bool:
        return self._sync_enabled

    @property
    def is_syncing(self) -> bool:
        return self._is_syncing

    def toggle_sync(self) -> bool:
        """Toggle sync on/off. Returns new state."""
        self._sync_enabled = not self._sync_enabled
        return self._sync_enabled

    def enter_sync(self) -> None:
        """Enter sync-suppression mode (during pane rebuilds)."""
        self._is_syncing = True

    def exit_sync(self) -> None:
        """Exit sync-suppression mode."""
        self._is_syncing = False

    def sync_from_project(
        self,
        project,
        rel_index,
        *,
        project_list: SyncableProjectList,
        detail_pane: SyncableDetailPane,
        worktree_pane: SyncableWorktreePane,
        terminal_pane: SyncableTerminalPane,
    ) -> None:
        """Drive all panes when project highlight changes."""
        if self._is_syncing or not self._sync_enabled or rel_index is None:
            return
        self._is_syncing = True
        try:
            resolver_wts = rel_index.worktrees_for(project)
            resolver_terms = rel_index.terminals_for(project)
            detail_pane.show_project(
                project,
                resolver_worktrees=resolver_wts,
                resolver_terminals=resolver_terms,
            )
            if resolver_wts:
                wt = resolver_wts[0]
                if not worktree_pane.sync_to(wt.repo_name, wt.branch):
                    worktree_pane.clear_selection()
            else:
                worktree_pane.clear_selection()
            if resolver_terms:
                if not terminal_pane.sync_to(resolver_terms[0].session_name):
                    terminal_pane.clear_selection()
            else:
                terminal_pane.clear_selection()
        finally:
            self._is_syncing = False

    def sync_from_worktree(
        self,
        worktree,
        rel_index,
        *,
        project_list: SyncableProjectList,
        detail_pane: SyncableDetailPane,
        worktree_pane: SyncableWorktreePane,
        terminal_pane: SyncableTerminalPane,
    ) -> None:
        """Drive ProjectList and TerminalPane based on highlighted worktree."""
        if self._is_syncing or not self._sync_enabled or rel_index is None:
            return
        self._is_syncing = True
        try:
            project = rel_index.project_for_worktree(worktree)
            if project is not None:
                project_list.sync_to(project.name)
                resolver_wts = rel_index.worktrees_for(project)
                resolver_terms = rel_index.terminals_for(project)
                detail_pane.show_project(
                    project,
                    resolver_worktrees=resolver_wts,
                    resolver_terminals=resolver_terms,
                )
                if resolver_terms:
                    if not terminal_pane.sync_to(resolver_terms[0].session_name):
                        terminal_pane.clear_selection()
                else:
                    terminal_pane.clear_selection()
            else:
                terminal_pane.clear_selection()
        finally:
            self._is_syncing = False

    def sync_from_session(
        self,
        session_name: str,
        rel_index,
        *,
        project_list: SyncableProjectList,
        detail_pane: SyncableDetailPane,
        worktree_pane: SyncableWorktreePane,
        terminal_pane: SyncableTerminalPane,
    ) -> None:
        """Drive ProjectList and WorktreePane based on highlighted terminal."""
        if self._is_syncing or not self._sync_enabled or rel_index is None:
            return
        self._is_syncing = True
        try:
            project = rel_index.project_for_terminal(session_name)
            if project is not None:
                project_list.sync_to(project.name)
                worktrees = rel_index.worktrees_for(project)
                terminals = rel_index.terminals_for(project)
                detail_pane.show_project(
                    project,
                    resolver_worktrees=worktrees,
                    resolver_terminals=terminals,
                )
                if worktrees:
                    wt = worktrees[0]
                    if not worktree_pane.sync_to(wt.repo_name, wt.branch):
                        worktree_pane.clear_selection()
                else:
                    worktree_pane.clear_selection()
            else:
                worktree_pane.clear_selection()
        finally:
            self._is_syncing = False
```

**Key design points:**
- Uses `Protocol` interfaces (PEP 544) -- no Textual imports whatsoever
- The existing widgets already implement `sync_to()` and `clear_selection()` -- they satisfy the protocols with zero changes
- `_is_syncing` guard moves here from app.py
- `_sync_enabled` state moves here from app.py
- `enter_sync()` / `exit_sync()` for pane rebuild suppression (replaces inline `self._is_syncing = True` in app.py)

**Confidence:** HIGH -- the existing `sync_to()` / `clear_selection()` methods on all panes already match the Protocol signatures perfectly. This is not speculative; the interfaces exist.

#### 2b. DataOrchestrator (`src/joy/orchestrator.py`)

**Responsibility:** Background data loading coordination, ready-flag management, relationship computation trigger, and propagation logic.

**What moves here from app.py:**
- `_worktrees_ready` / `_sessions_ready` flags
- `_current_worktrees` / `_current_sessions` / `_current_mr_data` / `_current_mr_authored` caches
- `_maybe_compute_relationships()` logic
- `_propagate_mr_auto_add()` and `_propagate_changes()` business logic
- `_apply_worktree_link_status_fast()` logic

```python
"""Background data orchestration. Pure Python, no Textual."""
from __future__ import annotations

from dataclasses import dataclass, field

from joy.models import Config, PresetKind, ObjectItem, Project, Repo, TerminalSession, WorktreeInfo
from joy.resolver import RelationshipIndex, compute_relationships


@dataclass
class RefreshResult:
    """Outcome of a data refresh cycle, consumed by the app layer."""
    rel_index: RelationshipIndex | None = None
    mr_messages: list[str] = field(default_factory=list)
    needs_save: bool = False
    linked_paths: set[str] = field(default_factory=set)
    linked_branches: set[tuple[str, str]] = field(default_factory=set)


class DataOrchestrator:
    """Coordinates data loading and relationship computation.

    Holds cached data from background workers. When both worktree and
    terminal data are ready, computes relationships and propagation.
    No Textual imports. No widget references.
    """

    def __init__(self) -> None:
        self._worktrees_ready: bool = False
        self._sessions_ready: bool = False
        self._current_worktrees: list[WorktreeInfo] = []
        self._current_sessions: list[TerminalSession] = []
        self._current_mr_data: dict = {}
        self._current_mr_authored: list = []
        self._rel_index: RelationshipIndex | None = None

    @property
    def rel_index(self) -> RelationshipIndex | None:
        return self._rel_index

    @property
    def current_worktrees(self) -> list[WorktreeInfo]:
        return self._current_worktrees

    @property
    def current_sessions(self) -> list[TerminalSession]:
        return self._current_sessions

    @property
    def current_mr_data(self) -> dict:
        return self._current_mr_data

    @property
    def current_mr_authored(self) -> list:
        return self._current_mr_authored

    def receive_worktrees(
        self,
        worktrees: list[WorktreeInfo],
        mr_data: dict,
        mr_authored: list,
        mr_failed: bool = False,
    ) -> None:
        """Called when worktree worker completes."""
        self._current_worktrees = worktrees
        self._current_mr_data = mr_data
        self._current_mr_authored = mr_authored
        self._worktrees_ready = True

    def receive_sessions(self, sessions: list[TerminalSession]) -> None:
        """Called when terminal worker completes."""
        self._current_sessions = sessions
        self._sessions_ready = True

    def try_compute(
        self,
        projects: list[Project],
        repos: list[Repo],
        config: Config,
    ) -> RefreshResult | None:
        """If both data sources ready, compute relationships and propagation.

        Returns RefreshResult if computation happened, None if not ready yet.
        Resets ready-flags after computation to prevent stale-data races.
        """
        if not (self._worktrees_ready and self._sessions_ready):
            return None

        self._worktrees_ready = False
        self._sessions_ready = False

        self._rel_index = compute_relationships(
            projects, self._current_worktrees, self._current_sessions, repos
        )

        result = RefreshResult(rel_index=self._rel_index)

        # MR auto-add propagation (moved from app.py)
        result.mr_messages = self._propagate_mr_auto_add(
            projects, self._current_mr_data, config
        )
        result.needs_save = any("\u2295 Added PR" in m for m in result.mr_messages)

        # Compute linked paths for worktree dim/highlight
        result.linked_paths = set(self._rel_index._project_for_wt_path.keys())
        result.linked_branches = set(self._rel_index._project_for_wt_branch.keys())

        return result

    @staticmethod
    def compute_linked_paths_fast(
        projects: list[Project],
        worktrees: list[WorktreeInfo],
    ) -> tuple[set[str], set[tuple[str, str]]]:
        """Fast path: compute linked worktree paths without full rel_index.

        Used for immediate styling before terminal data is available.
        Replicates the logic from app._apply_worktree_link_status_fast.
        """
        linked_paths: set[str] = set()
        linked_branches: set[tuple[str, str]] = set()
        for project in projects:
            for obj in project.objects:
                if obj.kind == PresetKind.WORKTREE:
                    if any(wt.path == obj.value for wt in worktrees):
                        linked_paths.add(obj.value)
                elif obj.kind == PresetKind.BRANCH and project.repo is not None:
                    if any(
                        wt.repo_name == project.repo and wt.branch == obj.value
                        for wt in worktrees
                    ):
                        linked_branches.add((project.repo, obj.value))
        return linked_paths, linked_branches

    @staticmethod
    def _propagate_mr_auto_add(
        projects: list[Project],
        mr_data: dict,
        config: Config,
    ) -> list[str]:
        """Auto-add MR objects for detected PRs. Returns notification messages."""
        messages: list[str] = []
        if not mr_data:
            return messages
        for (repo_name, branch), mr_info in mr_data.items():
            if not mr_info.url:
                continue
            for project in projects:
                if project.repo is None or project.repo != repo_name:
                    continue
                has_branch = any(
                    obj.kind == PresetKind.BRANCH and obj.value == branch
                    for obj in project.objects
                )
                if not has_branch:
                    continue
                already_has_mr = any(
                    obj.kind == PresetKind.MR and obj.value == mr_info.url
                    for obj in project.objects
                )
                if already_has_mr:
                    continue
                new_mr = ObjectItem(
                    kind=PresetKind.MR,
                    value=mr_info.url,
                    label=f"PR #{mr_info.mr_number}",
                    open_by_default=PresetKind.MR.value in config.default_open_kinds,
                )
                project.objects.append(new_mr)
                messages.append(f"\u2295 Added PR #{mr_info.mr_number} to {project.name}")
        return messages
```

**Key design points:**
- `RefreshResult` is a pure data object -- the app layer decides what to do with it (update widgets, save to disk, show notifications)
- MR propagation logic moved verbatim from app.py -- same algorithm, no Textual dependencies
- Ready-flag coordination is internal state, not exposed
- `compute_linked_paths_fast` is a static method -- testable in isolation

**Confidence:** HIGH -- direct extraction of existing code with no behavioral change.

#### 2c. ProjectService (`src/joy/services.py`)

**Responsibility:** Project CRUD operations (create, rename, delete, archive, unarchive) and config management.

**What moves here from app.py and widget action handlers:**
- Project creation logic (from `action_new_project`)
- Project deletion logic (from `ProjectList.action_delete_project`)
- Project archival logic (from `ProjectList.action_archive_project`)
- Unarchive logic (from `ProjectList.action_open_archive_browser`)
- Object add/edit/delete/toggle logic (from `ProjectDetail`)
- Config save operations

```python
"""Project lifecycle operations. No Textual imports."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol

from joy.models import (
    ArchivedProject, Config, ObjectItem, PresetKind, Project, Repo,
)


class StoragePort(Protocol):
    """Port: persistence operations."""
    def save_projects(self, projects: list[Project]) -> None: ...
    def load_projects(self) -> list[Project]: ...
    def save_config(self, config: Config) -> None: ...
    def load_config(self) -> Config: ...
    def load_repos(self) -> list[Repo]: ...
    def save_repos(self, repos: list[Repo]) -> None: ...
    def load_archived(self) -> list[ArchivedProject]: ...
    def save_archived(self, archived: list[ArchivedProject]) -> None: ...


class ProjectService:
    """Stateless project lifecycle operations."""

    def __init__(self, storage: StoragePort) -> None:
        self._storage = storage

    def create_project(
        self,
        name: str,
        projects: list[Project],
        *,
        repo: str | None = None,
        branch: str | None = None,
    ) -> Project | str:
        """Create a new project. Returns Project on success, error string on failure."""
        if any(p.name == name for p in projects):
            return f"Project '{name}' already exists"
        project = Project(name=name, repo=repo)
        if branch:
            project.objects.append(ObjectItem(kind=PresetKind.BRANCH, value=branch))
        projects.append(project)
        self._storage.save_projects(projects)
        return project

    def delete_project(
        self, project: Project, projects: list[Project]
    ) -> bool:
        """Remove a project from the list and persist. Returns success."""
        try:
            projects.remove(project)
        except ValueError:
            return False
        self._storage.save_projects(projects)
        return True

    def archive_project(
        self, project: Project, projects: list[Project]
    ) -> ArchivedProject | None:
        """Archive a project: strip volatile objects, move to archive."""
        try:
            projects.remove(project)
        except ValueError:
            return None
        stripped_objects = [
            obj for obj in project.objects
            if obj.kind not in (PresetKind.WORKTREE, PresetKind.TERMINALS)
        ]
        archived_project = Project(
            name=project.name,
            objects=stripped_objects,
            created=project.created,
            repo=project.repo,
        )
        archived = ArchivedProject(
            project=archived_project,
            archived_at=datetime.now(timezone.utc),
        )
        self._storage.save_projects(projects)
        existing_archived = self._storage.load_archived()
        existing_archived.append(archived)
        self._storage.save_archived(existing_archived)
        return archived

    def unarchive_project(
        self, archived: ArchivedProject, projects: list[Project]
    ) -> Project:
        """Restore an archived project to the live list."""
        projects.append(archived.project)
        self._storage.save_projects(projects)
        all_archived = self._storage.load_archived()
        updated = [ap for ap in all_archived if ap.project.name != archived.project.name]
        self._storage.save_archived(updated)
        return archived.project

    def add_object(
        self,
        project: Project,
        kind: PresetKind,
        value: str,
        config: Config,
        projects: list[Project],
    ) -> ObjectItem:
        """Add an object to a project and persist."""
        obj = ObjectItem(
            kind=kind,
            value=value,
            open_by_default=kind.value in config.default_open_kinds,
        )
        project.objects.append(obj)
        self._storage.save_projects(projects)
        return obj

    def rename_project(
        self, project: Project, new_name: str, projects: list[Project]
    ) -> str | None:
        """Rename a project. Returns error string on failure, None on success."""
        if any(p.name == new_name and p is not project for p in projects):
            return f"Project '{new_name}' already exists"
        project.name = new_name
        self._storage.save_projects(projects)
        return None
```

**Key design points:**
- `StoragePort` Protocol abstracts store.py -- tests can provide a fake in-memory store
- Methods are synchronous and stateless -- the `@work(thread=True)` decoration stays in app.py
- Validation logic (duplicate name check) moves from widget callbacks into the service
- Returns data/errors rather than calling `self.app.notify()` -- the app layer handles notifications

**Confidence:** HIGH -- direct extraction of existing logic, Protocol matches existing store.py API.

---

## 3. Widget Facade Methods (Public API Contract)

The biggest coupling problem is app.py and widgets reaching into each other's private fields. The fix is to add explicit public methods to each widget.

### ProjectDetail Facade

```python
# Add to project_detail.py

class ProjectDetail(Widget, can_focus=True):
    # ... existing code ...

    # NEW: Public facade methods replacing private field access

    @property
    def current_project(self) -> Project | None:
        """Read-only access to the displayed project."""
        return self._project

    @property
    def highlighted_item(self) -> ObjectItem | None:
        """Return the currently highlighted item (replaces highlighted_object)."""
        return self.highlighted_object  # alias existing property

    @property
    def all_rows(self) -> list:
        """Read-only access to current rows for iteration."""
        return list(self._rows)

    @property
    def default_items(self) -> list[ObjectItem]:
        """Return all items with open_by_default=True."""
        return [row.item for row in self._rows if row.item.open_by_default]

    def clear(self) -> None:
        """Clear all content -- replaces direct _project=None/_rows=[]/_cursor=-1."""
        self._project = None
        self._rows = []
        self._cursor = -1
        scroll = self.query_one("#detail-scroll")
        scroll.remove_children()

    # show_project is an alias for set_project (satisfies SyncableDetailPane protocol)
    def show_project(self, project, resolver_worktrees=None, resolver_terminals=None):
        self.set_project(project, resolver_worktrees=resolver_worktrees,
                         resolver_terminals=resolver_terminals)
```

### ProjectList Facade

```python
# Add to project_list.py

class ProjectList(Widget, can_focus=True):
    # ... existing code ...

    # NEW: Public facade methods

    @property
    def current_project(self) -> Project | None:
        """Return the currently highlighted project."""
        if 0 <= self._cursor < len(self._rows):
            return self._rows[self._cursor].project
        return None

    @property
    def has_cursor(self) -> bool:
        """Whether a valid cursor position exists."""
        return 0 <= self._cursor < len(self._rows)
```

### WorktreePane Addition

```python
# Add to worktree_pane.py

class WorktreePane(Widget, can_focus=True):
    # ... existing code ...

    @property
    def highlighted_path(self) -> str | None:
        """Return the path of the currently highlighted worktree."""
        if 0 <= self._cursor < len(self._rows):
            return self._rows[self._cursor].path
        return None
```

### TerminalPane and MRPane

These already have clean public APIs (`sync_to`, `clear_selection`, `set_sessions`, `set_mr_data`). No additions needed.

---

## 4. Dependency Injection Strategy

### Constructor Injection on App

Textual's `App.__init__` is the natural injection point. The services are created once and passed to `JoyApp`:

```python
class JoyApp(App):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        # Services (injected, replaceable for testing)
        self._coordinator = PaneCoordinator()
        self._orchestrator = DataOrchestrator()
        self._project_service = ProjectService(storage=_StoreAdapter())
        # Remaining app state (config, projects, repos, timers)
        self._config: Config = Config()
        self._projects: list[Project] = []
        self._repos: list[Repo] = []
        # ... timers only (no more flags, caches, or sync state)
```

### Store Adapter (bridges Protocol to existing store.py)

```python
class _StoreAdapter:
    """Adapts store.py module functions to the StoragePort Protocol."""

    def save_projects(self, projects):
        from joy.store import save_projects
        save_projects(projects)

    def load_projects(self):
        from joy.store import load_projects
        return load_projects()

    def save_config(self, config):
        from joy.store import save_config
        save_config(config)

    def load_config(self):
        from joy.store import load_config
        return load_config()

    def load_repos(self):
        from joy.store import load_repos
        return load_repos()

    def save_repos(self, repos):
        from joy.store import save_repos
        save_repos(repos)

    def load_archived(self):
        from joy.store import load_archived_projects
        return load_archived_projects()

    def save_archived(self, archived):
        from joy.store import save_archived_projects
        save_archived_projects(archived)
```

### Why Not a DI Container?

Python's `Protocol` (structural subtyping) + constructor injection is sufficient. A DI container (like `inject` or `dependency-injector`) would:
- Add a dependency to a project that values minimal dependencies
- Add indirection that makes the code harder to follow
- Be overkill for 3 services with clear ownership

The Textual community consensus (from GitHub Discussion #4107) is to store state as class attributes in `__init__`, which aligns perfectly with constructor injection of service objects.

---

## 5. Data Flow: Before and After

### Before (Current)

```
Background Thread (worktree worker)
  |
  v
app.call_from_thread(app._set_worktrees, ...)
  |
  v
app._set_worktrees():
  - stores worktrees in app._current_worktrees (state)
  - sets app._worktrees_ready = True (flag)
  - calls worktree_pane.set_worktrees() directly (coupling)
  - calls app._apply_worktree_link_status_fast() (business logic)
  - calls app._maybe_compute_relationships() (coordination)
    - if both ready:
      - calls compute_relationships() (pure)
      - calls app._update_badges() (widget mutation)
      - calls app._propagate_changes() (business logic + widget mutation)
```

### After (Refactored)

```
Background Thread (worktree worker -- still in app.py @work)
  |
  v
app.call_from_thread(app._on_worktrees_loaded, ...)
  |
  v
app._on_worktrees_loaded():
  - self._orchestrator.receive_worktrees(...)                       # pure state update
  - linked = DataOrchestrator.compute_linked_paths_fast(...)        # pure computation
  - self._coordinator.enter_sync()                                  # suppress sync
  - worktree_pane.set_worktrees(...)                                # widget update
  - self._coordinator.exit_sync()                                   # restore sync
  - worktree_pane.set_linked_paths(linked)                          # widget update
  - mr_pane.set_mr_data(...)                                        # widget update
  - result = self._orchestrator.try_compute(projects, repos, config)
  - if result:
      self._apply_refresh_result(result)                            # dispatch results
```

```
app._apply_refresh_result(result):
  - project_list.update_badges(result.rel_index, ...)              # widget update
  - worktree_pane.set_linked_paths(result.linked_paths, ...)       # widget update
  - if result.needs_save:
      self._save_projects_bg()                                     # persistence
  - if result.mr_messages:
      self._coordinator.enter_sync()
      project_list.set_projects(self._projects, self._repos)       # rebuild
      # re-show current project in detail if cursor valid
      self._coordinator.exit_sync()
  - for msg in result.mr_messages:
      self.notify(msg)                                             # UI feedback
```

**The key shift:** App methods become thin dispatchers that:
1. Call a service method (pure logic, returns data)
2. Apply the result to widgets (UI updates)
3. Trigger side effects (save, notify)

Business logic never touches widgets. Widget updates never compute business logic.

---

## 6. Module Structure

### New Files

| File | LOC (est.) | Purpose |
|------|-----------|---------|
| `src/joy/coordinator.py` | ~180 | PaneCoordinator with Protocol interfaces |
| `src/joy/orchestrator.py` | ~200 | DataOrchestrator with RefreshResult |
| `src/joy/services.py` | ~150 | ProjectService with StoragePort |
| `tests/test_coordinator.py` | ~200 | Fast unit tests, no TUI |
| `tests/test_orchestrator.py` | ~250 | Fast unit tests, no TUI |
| `tests/test_services.py` | ~200 | Fast unit tests with fake StoragePort |

### Modified Files

| File | Changes | Risk |
|------|---------|------|
| `src/joy/app.py` | Remove business logic, add service delegation | HIGH (largest change) |
| `src/joy/widgets/project_list.py` | Add facade properties, replace `self.app._*` calls | MEDIUM |
| `src/joy/widgets/project_detail.py` | Add `clear()`, `show_project()`, `default_items` | LOW |
| `src/joy/widgets/worktree_pane.py` | Add `highlighted_path` property | LOW |
| `src/joy/widgets/terminal_pane.py` | No changes needed (public API already clean) | NONE |
| `src/joy/widgets/mr_pane.py` | No changes needed | NONE |

### Untouched Files

| File | Reason |
|------|--------|
| `src/joy/models.py` | Already pure domain |
| `src/joy/store.py` | Already clean adapter |
| `src/joy/resolver.py` | Already pure function |
| `src/joy/dispatch.py` | Already data-only |
| `src/joy/operations.py` | Already clean adapter |
| `src/joy/worktrees.py` | Already pure functions |
| `src/joy/mr_status.py` | Already I/O adapter |
| `src/joy/terminal_sessions.py` | Already I/O adapter |
| `src/joy/screens/*` | Modals are already self-contained |

---

## 7. Testing Strategy

### Three-Layer Testing Pyramid

```
        /  Snapshot Tests  \      <-- ~5 tests, visual regression only
       /  Widget Tests      \     <-- ~30 tests, Textual pilot, fake services
      /  Service Tests       \    <-- ~50+ tests, fast, no TUI, pure Python
```

#### Layer 1: Service Tests (Fast, No TUI)

```python
# tests/test_coordinator.py
class FakeProjectList:
    """Test double satisfying SyncableProjectList Protocol."""
    def __init__(self):
        self.synced_to: str | None = None
        self.cleared: bool = False

    def sync_to(self, project_name: str) -> bool:
        self.synced_to = project_name
        return True

    def clear_selection(self) -> None:
        self.cleared = True


def test_sync_from_project_drives_worktree_pane():
    coordinator = PaneCoordinator()
    fake_wt = FakeWorktreePane()
    fake_term = FakeTerminalPane()
    fake_detail = FakeDetailPane()
    fake_list = FakeProjectList()

    project = Project(name="test", repo="my-repo")
    rel_index = make_rel_index(project, worktrees=[...])

    coordinator.sync_from_project(
        project, rel_index,
        project_list=fake_list,
        detail_pane=fake_detail,
        worktree_pane=fake_wt,
        terminal_pane=fake_term,
    )

    assert fake_wt.synced_to == ("my-repo", "feature-x")
```

**Speed advantage:** These tests run in <0.1s each with zero Textual imports. The current test_sync.py tests take ~10s each because they spin up the full TUI.

#### Layer 2: Widget Tests (Textual Pilot, Fake Backend)

```python
# tests/test_widget_integration.py
async def test_project_detail_clear():
    """Test the clear() facade method works correctly."""
    async with ProjectDetail().run_test() as pilot:
        detail = pilot.app.query_one(ProjectDetail)
        detail.set_project(some_project)
        detail.clear()
        assert detail.current_project is None
```

#### Layer 3: Snapshot Tests (Sparingly)

Only for visual regression of the full 5-pane layout. Use `compare_snapshots` from Textual's testing API. Maximum 5 snapshots.

---

## 8. Migration Path (Build Order)

**Guiding principle:** Each step must leave all existing tests passing. No big-bang rewrite.

### Step 1: Add Widget Facade Methods (LOW risk)

Add the public methods (`current_project`, `default_items`, `clear()`, `show_project()`, `highlighted_path`) to widgets. These are additive -- nothing breaks.

**Verification:** Run existing test suite. All tests pass. The new methods are unused.

### Step 2: Create PaneCoordinator (MEDIUM risk)

Create `coordinator.py` with the Protocol interfaces and PaneCoordinator class. Write tests for it using fake panes. The coordinator is pure Python -- no Textual dependency.

**Verification:** New tests pass. Existing tests still pass (PaneCoordinator not yet wired in).

### Step 3: Wire PaneCoordinator into app.py (MEDIUM risk)

Replace the inline `_sync_from_project`, `_sync_from_worktree`, `_sync_from_session` methods in app.py with delegates to `self._coordinator`. Remove `_is_syncing` and `_sync_enabled` from app.py.

**Before:**
```python
def _sync_from_project(self, project):
    self._is_syncing = True
    try:
        # ... 25 lines of sync logic
    finally:
        self._is_syncing = False
```

**After:**
```python
def _sync_from_project(self, project):
    self._coordinator.sync_from_project(
        project,
        self._orchestrator.rel_index,
        project_list=self.query_one(ProjectList),
        detail_pane=self.query_one(ProjectDetail),
        worktree_pane=self.query_one(WorktreePane),
        terminal_pane=self.query_one(TerminalPane),
    )
```

**Verification:** All existing sync tests pass. Cross-pane sync behavior identical.

### Step 4: Create DataOrchestrator (MEDIUM risk)

Create `orchestrator.py` with DataOrchestrator and RefreshResult. Write tests for it using fixture data. No Textual dependency.

**Verification:** New tests pass. Existing tests still pass (DataOrchestrator not yet wired in).

### Step 5: Wire DataOrchestrator into app.py (HIGH risk -- most impactful)

Replace the inline `_set_worktrees`, `_set_terminal_sessions`, `_maybe_compute_relationships`, `_propagate_changes`, `_propagate_mr_auto_add`, and `_apply_worktree_link_status_fast` methods with orchestrator calls.

This is the largest single change. The `_set_worktrees` method alone is 35 lines with 5 different responsibilities. After refactoring, it becomes a thin dispatcher.

**Verification:** All existing tests pass. Manual smoke test of full refresh cycle.

### Step 6: Create ProjectService (MEDIUM risk)

Create `services.py` with ProjectService and StoragePort. Write tests with a fake storage adapter.

**Verification:** New tests pass. Existing tests still pass.

### Step 7: Wire ProjectService into widgets (MEDIUM risk)

Replace `self.app._save_projects_bg()` calls in widgets with `self.app._project_service` calls. Replace duplicate validation logic in widget callbacks with service method calls.

This step also removes the `self.app._projects` direct access from widgets -- instead, widgets receive data through their public `set_*` methods, and request mutations through the service.

**Verification:** All existing tests pass.

### Step 8: Replace Private Field Access (LOW risk, many small changes)

Systematically replace every `detail._project`, `detail._rows`, `detail._cursor`, `pane._cursor`, `pane._rows` access in app.py and cross-widget calls with the facade properties from Step 1.

**Verification:** `grep -r '\._project[^_s]' --include='*.py'` shows no cross-module private access remaining.

### Step 9: Audit and Clean (LOW risk)

- Remove unused methods from app.py
- Update app.py instance variable count (target: <10, down from 21)
- Run full test suite including slow tests
- Verify LOC reduction in app.py (target: ~400 LOC, down from 1,058)

---

## 9. Anti-Patterns to Avoid

### Anti-Pattern 1: Over-Abstracting Textual's @work

**What:** Trying to move `@work(thread=True)` decorators into the service layer.
**Why bad:** `@work` depends on `self.app` being a mounted Textual App. The service layer must not import Textual.
**Instead:** Keep `@work` methods in app.py. They call service methods synchronously inside the thread, then push results back via `call_from_thread`.

### Anti-Pattern 2: Event Bus Between Services

**What:** Creating a custom event/message system for services to communicate.
**Why bad:** Textual already has a message system. Adding another creates two event systems that must be kept in sync.
**Instead:** Services return data. The app layer dispatches results to widgets using Textual's existing mechanisms.

### Anti-Pattern 3: Making Services Aware of Each Other

**What:** Having PaneCoordinator import DataOrchestrator or vice versa.
**Why bad:** Creates a second dependency graph parallel to the app layer.
**Instead:** App.py is the composition root. It calls orchestrator, gets results, passes them to coordinator. Services are independent.

### Anti-Pattern 4: Protocol Explosion

**What:** Creating a Protocol for every method on every widget.
**Why bad:** Joy has 5 pane widgets. If each needs a Protocol with 10 methods, that is 50 Protocol methods to maintain.
**Instead:** Only create Protocols for the sync-related methods that PaneCoordinator needs (~3 methods per Protocol, ~4 Protocols). Other widget interactions stay as direct calls through `query_one()`.

### Anti-Pattern 5: Premature Service Splitting

**What:** Splitting ProjectService into CreateProjectService, DeleteProjectService, etc.
**Why bad:** Joy is a personal tool with <20 operations. One service per bounded context is the right granularity.
**Instead:** ProjectService handles all project lifecycle operations. If it exceeds ~300 LOC, reconsider.

---

## 10. Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Sync behavior regression | MEDIUM | HIGH | PaneCoordinator tests + existing sync tests |
| Worker thread timing changes | LOW | HIGH | Keep @work methods in app.py unchanged |
| Widget initialization order issues | LOW | MEDIUM | Facades are additive; fallback to existing patterns |
| Test suite churn | MEDIUM | MEDIUM | Each step leaves existing tests green |
| Performance regression from indirection | LOW | LOW | One extra method call per operation, negligible |

---

## 11. Estimated Impact

### Before

| Metric | Value |
|--------|-------|
| app.py LOC | 1,058 |
| app.py instance variables | 21 |
| Cross-module private field access | ~25 locations |
| Business logic in app.py | ~150 LOC |
| Sync logic in app.py | ~120 LOC |
| Testable without TUI | models, store, resolver, operations only |

### After (Projected)

| Metric | Value |
|--------|-------|
| app.py LOC | ~400 |
| app.py instance variables | ~8 (config, projects, repos, 3 services, 2 timers) |
| Cross-module private field access | 0 |
| Business logic in services | ~350 LOC across 3 files |
| Testable without TUI | + coordinator, orchestrator, project_service |
| New fast tests | ~50+ |

---

## Sources

- Textual official documentation: https://textual.textualize.io/
- Textual GitHub Discussion #4107 (state management): https://github.com/Textualize/textual/discussions/4107
- Textual input/key bindings: https://textual.textualize.io/guide/input/
- Python PEP 544 (Protocols): https://peps.python.org/pep-0544/
- Hexagonal Architecture in Python: https://softwarepatternslexicon.com/python/architectural-patterns/hexagonal-architecture-ports-and-adapters/
- Python Service Layer Pattern: https://dev.to/alexis_jean/organize-your-code-with-the-service-layer-pattern-a-simple-python-example-2pnn
- Direct codebase analysis of joy v1.3 (6,180 src LOC)
