# Architecture Patterns: Cross-Pane Sync & Live Data Propagation

**Domain:** Cross-pane intelligence for a 4-pane Textual TUI
**Researched:** 2026-04-14
**Overall confidence:** HIGH

---

## Recommended Architecture

The v1.2 architecture introduces three new concerns on top of the existing codebase:

1. **Relationship resolution** -- given an item in any pane, compute related items in the other three panes
2. **Cross-pane cursor sync** -- when the user moves the cursor in one pane, move cursors in other panes to the best matching related item
3. **Live data propagation** -- after background refresh, diff discovered worktrees/agents against project objects and mutate projects.toml

These concerns are layered on top of the existing worker/refresh architecture. The architecture below keeps each concern in a separate module with clear boundaries.

### System Diagram

```
                     JoyApp (app.py)
                        |
          +-------------+-------------+
          |             |             |
    _load_worktrees  _load_terminal  (existing workers)
          |             |
          v             v
    _set_worktrees  _set_terminal_sessions
          |             |
          +------+------+
                 |
                 v
         _on_live_data_ready()  <-- NEW: orchestrator method
                 |
          +------+------+
          |             |
          v             v
    propagator       resolver.build_index()
    .propagate()         |
          |              v
          v         RelationshipIndex  <-- NEW: pure data structure
    projects.toml       |
    (mutated)           |
          |             v
          v        sync_controller    <-- NEW: app-level coordinator
    _refresh_all_panes()   |
                           v
                    pane.sync_to(item) <-- NEW: method on each pane
```

### Component Boundaries

| Component | Location | Responsibility | Communicates With |
|-----------|----------|---------------|-------------------|
| **RelationshipIndex** | `resolver.py` (new) | Pure data: maps any item key to related items in other panes | Nothing -- pure lookup table |
| **build_index()** | `resolver.py` (new) | Builds RelationshipIndex from current projects + live worktrees + live sessions | models.py data only |
| **SyncController** | `sync.py` (new) | Coordinates cross-pane cursor sync; owns the sync-enabled flag; guards against loops | Pane widgets (via app.query_one) |
| **propagate()** | `propagator.py` (new) | Diffs live data against project objects, returns mutations | models.py, store.py |
| **JoyApp** | `app.py` (modified) | Orchestrates: after refresh, runs propagator then rebuilds index then triggers sync | All new modules |
| **ProjectList** | `project_list.py` (modified) | Accepts sync_to() calls; posts SyncRequested message on cursor move | SyncController (indirectly via messages) |
| **WorktreePane** | `worktree_pane.py` (modified) | Accepts sync_to() calls; posts SyncRequested message on cursor move | SyncController (indirectly via messages) |
| **TerminalPane** | `terminal_pane.py` (modified) | Accepts sync_to() calls; posts SyncRequested message on cursor move | SyncController (indirectly via messages) |
| **ProjectDetail** | `project_detail.py` (modified) | Passive recipient only -- syncs when project changes | No sync messages posted |

---

## New Module: resolver.py -- Relationship Resolution

### Placement: Standalone Module, Not Mixin

The resolver belongs in its own module (`src/joy/resolver.py`), not as an app mixin or widget method. Reasons:

1. **Pure logic, no I/O, no widgets.** The resolver takes data in, returns data out. It has no business touching Textual's DOM.
2. **Independently testable.** A mixin would require instantiating a Textual App to test. A standalone module needs only dataclass instances.
3. **Called from multiple places.** Both the sync controller and the propagator need relationship data. A mixin on one widget would create awkward coupling.
4. **Follows the existing pattern.** `worktrees.py`, `mr_status.py`, and `terminal_sessions.py` are all standalone modules for data logic. The resolver is the same shape.

### Data Model

```python
# resolver.py
from __future__ import annotations

from dataclasses import dataclass, field
from joy.models import Project, WorktreeInfo, TerminalSession


@dataclass(frozen=True)
class ItemKey:
    """Universal key identifying any item across all panes.

    pane: "project" | "worktree" | "terminal"
    identity: unique string within that pane
        - project: project.name
        - worktree: f"{repo_name}:{branch}"
        - terminal: session_id
    """
    pane: str
    identity: str


@dataclass
class RelationshipIndex:
    """Bidirectional lookup: for any ItemKey, find related ItemKeys in other panes.

    Built once per refresh cycle. Immutable after construction (replace, don't mutate).
    """
    _related: dict[ItemKey, set[ItemKey]] = field(default_factory=dict)

    def get_related(self, key: ItemKey) -> set[ItemKey]:
        """Return all related items across other panes."""
        return self._related.get(key, set())

    def get_related_in_pane(self, key: ItemKey, pane: str) -> list[ItemKey]:
        """Return related items filtered to a specific pane, sorted for determinism."""
        return sorted(
            (k for k in self.get_related(key) if k.pane == pane),
            key=lambda k: k.identity,
        )
```

### Relationship Rules

These are the matching rules, in priority order:

| Relationship | Match Criterion | Direction |
|-------------|----------------|-----------|
| Project <-> Worktree | Project has a worktree object whose `value` (path) matches `WorktreeInfo.path`, OR project's branch object matches `WorktreeInfo.branch` | Bidirectional |
| Project <-> Worktree (repo) | Project's `repo` field matches `WorktreeInfo.repo_name` | Bidirectional |
| Project <-> Terminal | Project has an agents object whose `value` matches `TerminalSession.session_name` | Bidirectional |
| Worktree <-> Terminal | Terminal session's `cwd` starts with worktree's `path` (the agent is running inside that worktree) | Bidirectional |

### Build Function

```python
def build_index(
    projects: list[Project],
    worktrees: list[WorktreeInfo],
    sessions: list[TerminalSession] | None,
) -> RelationshipIndex:
    """Build a fresh RelationshipIndex from current state.

    Called after each refresh cycle completes. O(P*W + P*S + W*S)
    where P=projects, W=worktrees, S=sessions. For typical counts
    (<50 projects, <30 worktrees, <20 sessions) this is <30K comparisons -- trivial.
    """
    index = RelationshipIndex()
    # ... build bidirectional mappings ...
    return index
```

### Why Rebuild-On-Refresh, Not Incremental

The data set is tiny (dozens of items). Rebuilding the entire index after each 30s refresh is simpler and cheaper than tracking incremental changes. Incremental updates would require diffing old vs new worktrees/sessions and updating edges -- more code, more bugs, no measurable perf win.

**Confidence: HIGH** -- pure dataclass logic, no Textual API dependency, straightforward to test.

---

## New Module: sync.py -- Cross-Pane Sync Controller

### Placement: Standalone Coordinator, Instantiated by App

The sync controller is not a widget. It is a plain Python object instantiated and owned by JoyApp. It holds the sync-enabled flag, the current RelationshipIndex, and the loop guard.

```python
# sync.py
from __future__ import annotations

from joy.resolver import ItemKey, RelationshipIndex


class SyncController:
    """Coordinates cross-pane cursor sync.

    Owned by JoyApp. Not a widget -- has no DOM presence.
    """

    def __init__(self) -> None:
        self.enabled: bool = True
        self._index: RelationshipIndex = RelationshipIndex()
        self._syncing: bool = False  # loop guard

    def update_index(self, index: RelationshipIndex) -> None:
        """Replace the relationship index (called after each refresh)."""
        self._index = index

    def handle_cursor_move(self, source_key: ItemKey, app) -> None:
        """Called when cursor moves in any pane. Syncs related panes.

        The loop guard (_syncing) prevents infinite recursion:
        Pane A cursor moves -> sync fires -> Pane B cursor moves ->
        sync fires again -> but _syncing is True, so it returns immediately.
        """
        if not self.enabled or self._syncing:
            return

        self._syncing = True
        try:
            related = self._index.get_related(source_key)
            # Group by pane, find first match in each
            for pane_name in ("project", "worktree", "terminal"):
                if source_key.pane == pane_name:
                    continue  # don't sync back to source
                targets = self._index.get_related_in_pane(source_key, pane_name)
                if targets:
                    _sync_pane(app, pane_name, targets[0])
        finally:
            self._syncing = False
```

### Sync Loop Guard: Why a Simple Boolean Works

The guard is a boolean `_syncing` flag, not a lock or semaphore. This works because:

1. **Textual is single-threaded for UI.** All cursor moves and message handling run on the main asyncio event loop. There is no concurrent access to `_syncing`.
2. **Sync is synchronous.** `handle_cursor_move` calls `_sync_pane` which calls `pane.sync_to()` which sets `_cursor` and calls `_update_highlight()`. All of this happens in one synchronous call chain. No awaits, no deferred callbacks.
3. **The guard prevents re-entry, not concurrency.** The scenario is: cursor move in A -> `handle_cursor_move(A)` -> sets B cursor -> B's `_update_highlight` would normally post a highlight message -> that message would call `handle_cursor_move(B)` -> but `_syncing` is True, so it returns.

A more complex guard (per-pane locks, message-type filtering, generation counters) would be over-engineering. The boolean flag has zero failure modes in a single-threaded event loop.

**Alternative considered: Textual's `prevent()` context manager.** This suppresses specific message types during programmatic updates. It would work for preventing re-entrant messages, but requires the pane widgets to know about sync-specific message types. The boolean guard on the controller is simpler and keeps sync logic out of the pane widgets.

**Confidence: HIGH** -- single-threaded event loop guarantees no concurrent access. Pattern is well-established in UI frameworks.

### Sync Toggle

```python
# In JoyApp
BINDINGS = [
    # ... existing ...
    Binding("S", "toggle_sync", "Sync", priority=True),
]

def action_toggle_sync(self) -> None:
    self._sync_controller.enabled = not self._sync_controller.enabled
    state = "on" if self._sync_controller.enabled else "off"
    self.notify(f"Sync {state}", markup=False)
```

The toggle is app-level because sync is a global behavior, not per-pane.

### How Panes Participate in Sync

Each pane needs two additions:

1. **`sync_to(key: ItemKey)` method** -- move cursor to the row matching the given key, without triggering a sync cascade (the controller's `_syncing` flag handles this).
2. **Post a notification on cursor move** -- so the controller can react. This integrates into existing `_update_highlight()` methods.

The notification uses Textual's message bubbling. Each pane posts a `CursorMoved` message that bubbles to the App, where the handler calls `self._sync_controller.handle_cursor_move(key, self)`.

```python
# Shared message class (can live in a common messages.py or in sync.py)
class CursorMoved(Message):
    """Posted by any pane when its cursor moves to a new item."""
    def __init__(self, key: ItemKey) -> None:
        self.key = key
        super().__init__()
```

**Why not a reactive attribute on App?** Because cursor position is per-pane and the App would need separate reactives for each pane's cursor. Messages are the right tool for "something happened" events that need coordination.

---

## New Module: propagator.py -- Live Data Propagation

### Placement: Standalone Module

Like the resolver, the propagator is pure logic operating on data models. It takes the current projects and live-discovered data, computes mutations, and returns them. The App applies mutations and persists.

```python
# propagator.py
from __future__ import annotations

from dataclasses import dataclass
from joy.models import ObjectItem, PresetKind, Project, WorktreeInfo, TerminalSession


@dataclass
class PropagationResult:
    """Describes all mutations to apply to projects after a refresh cycle."""
    added_worktrees: list[tuple[str, ObjectItem]]    # (project_name, new_object)
    removed_worktrees: list[tuple[str, ObjectItem]]   # (project_name, removed_object)
    moved_worktrees: list[tuple[str, str, ObjectItem]] # (from_project, to_project, object)
    added_mrs: list[tuple[str, ObjectItem]]           # (project_name, new_mr_object)
    stale_agents: list[tuple[str, ObjectItem]]        # (project_name, object_to_mark_stale)
    unstale_agents: list[tuple[str, ObjectItem]]      # (project_name, object_to_unmark)
    dirty: bool = False  # True if any mutation was made


def propagate(
    projects: list[Project],
    worktrees: list[WorktreeInfo],
    sessions: list[TerminalSession] | None,
    mr_data: dict | None = None,
) -> PropagationResult:
    """Compute mutations needed to sync project objects with live data.

    Rules:
    1. Worktree discovered for project (by repo match + branch) but no worktree
       object exists -> add worktree object silently
    2. Worktree object exists but worktree no longer discovered -> remove object
    3. Worktree branch matches a DIFFERENT project's branch object -> move
       worktree object to that project ("branch is king")
    4. MR discovered for project's active branch -> add MR object if not present
    5. Agent session name matches project's agent object but session gone -> mark stale
    6. Agent session reappears -> clear stale mark

    Only operates on projects with a `repo` field (projects without repo are
    excluded from live sync per requirement).
    """
    # ... pure logic, returns PropagationResult ...
```

### Where Propagation Runs in the Refresh Cycle

Propagation runs **after** both `_set_worktrees` and `_set_terminal_sessions` complete, not inside the worker threads. This is because:

1. Propagation needs access to `self._projects` (app-level state) which should only be read/written on the main thread.
2. Propagation may mutate projects, which triggers a save and UI refresh.
3. Both worktree and terminal data must be available before propagation can run.

The orchestration in JoyApp:

```python
# app.py additions

def __init__(self, **kwargs) -> None:
    super().__init__(**kwargs)
    # ... existing ...
    self._sync_controller = SyncController()
    self._live_worktrees: list[WorktreeInfo] = []
    self._live_sessions: list[TerminalSession] | None = None
    self._worktrees_ready: bool = False
    self._terminals_ready: bool = False

async def _set_worktrees(self, worktrees, ...):
    # ... existing code ...
    self._live_worktrees = worktrees
    self._worktrees_ready = True
    self._maybe_run_propagation()

async def _set_terminal_sessions(self, sessions):
    # ... existing code ...
    self._live_sessions = sessions
    self._terminals_ready = True
    self._maybe_run_propagation()

def _maybe_run_propagation(self) -> None:
    """Run propagation + index rebuild when both data sources are ready."""
    if not (self._worktrees_ready and self._terminals_ready):
        return
    self._worktrees_ready = False
    self._terminals_ready = False

    # 1. Propagate live data to project objects
    result = propagate(
        self._projects, self._live_worktrees, self._live_sessions
    )
    if result.dirty:
        self._apply_propagation(result)
        self._save_projects_bg()
        # Refresh project list to show updated badge counts
        self.query_one(ProjectList).set_projects(self._projects, self._repos)

    # 2. Rebuild relationship index
    index = build_index(self._projects, self._live_worktrees, self._live_sessions)
    self._sync_controller.update_index(index)
```

### Ready-Flag Pattern vs. asyncio.gather

The "both ready" check uses simple boolean flags rather than `asyncio.gather` or `asyncio.Event`. This is because the two workers (`_load_worktrees` and `_load_terminal`) already use `call_from_thread` to push results to the main thread independently. Adding asyncio coordination would require restructuring the worker pattern. The boolean flags are simpler and fit the existing architecture.

**Confidence: HIGH** -- pure data transformation, no Textual API dependency, testable with dataclass instances.

---

## Badge Counts on Project Rows

Badge counts (worktree count + agent count) derive from the RelationshipIndex. After each index rebuild, the app pushes badge data to ProjectList.

### Implementation

```python
# In ProjectList
class ProjectRow(Static):
    def __init__(self, project: Project, *, badges: dict | None = None, **kwargs):
        self.project = project
        self._badges = badges or {}
        label = self._format_label(project, self._badges)
        super().__init__(label, **kwargs)

    @staticmethod
    def _format_label(project: Project, badges: dict) -> str:
        wt_count = badges.get("worktrees", 0)
        agent_count = badges.get("agents", 0)
        parts = [f" {project.name}"]
        if wt_count or agent_count:
            badge_parts = []
            if wt_count:
                badge_parts.append(f"{wt_count}")  # folder icon + count
            if agent_count:
                badge_parts.append(f"{agent_count}")  # terminal icon + count
            parts.append(f"  {'  '.join(badge_parts)}")
        return "".join(parts)
```

Badge data flows from App to ProjectList:

```python
# In JoyApp, after index rebuild
def _push_badge_counts(self) -> None:
    badges: dict[str, dict[str, int]] = {}
    for project in self._projects:
        key = ItemKey(pane="project", identity=project.name)
        wt_keys = self._sync_controller._index.get_related_in_pane(key, "worktree")
        term_keys = self._sync_controller._index.get_related_in_pane(key, "terminal")
        badges[project.name] = {
            "worktrees": len(wt_keys),
            "agents": len([k for k in term_keys
                          if True]),  # count all related terminal sessions
        }
    self.query_one(ProjectList).set_badges(badges)
```

ProjectList stores badges and applies them during `_rebuild()`. No full re-render needed if only badges change -- use a targeted `update_badges()` method that updates existing row labels in-place.

**Confidence: HIGH** -- straightforward data derivation, no new patterns.

---

## Patterns to Follow

### Pattern 1: Data Down, Messages Up (Textual Idiom)

**What:** Widgets receive data through method calls and attributes set by the parent/app. Widgets communicate upward through Textual Messages that bubble through the DOM.

**When:** Always, for all new inter-component communication.

**Applied to v1.2:**
- App pushes RelationshipIndex to SyncController (data down)
- App pushes badge counts to ProjectList (data down)
- App calls `pane.sync_to(key)` through SyncController (data down)
- Panes post `CursorMoved` messages (messages up)
- App handles `CursorMoved` and delegates to SyncController (app as mediator)

### Pattern 2: Rebuild-Not-Mutate for Derived State

**What:** When the source data changes, rebuild the derived data structure from scratch rather than trying to incrementally update it.

**When:** The data set is small enough that rebuilding is cheap (<1ms).

**Applied to v1.2:**
- RelationshipIndex is rebuilt after every refresh, not incrementally patched
- Badge counts are recomputed after every index rebuild
- This eliminates an entire class of stale-state bugs

### Pattern 3: Ready-Flags for Multi-Source Coordination

**What:** When an action requires data from multiple async sources, use boolean flags to track readiness and fire when all sources are ready.

**When:** Sources complete independently via `call_from_thread` and coordination must happen on the main thread.

**Applied to v1.2:**
- `_worktrees_ready` and `_terminals_ready` flags gate `_maybe_run_propagation()`
- Each flag is set in the respective `_set_*` callback
- The method resets both flags after running to prepare for the next refresh cycle

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Pane-to-Pane Direct Communication

**What:** Having WorktreePane directly call methods on ProjectList or vice versa.

**Why bad:** Creates tight coupling between sibling widgets. Any pane change requires updating all connected panes. Violates Textual's "messages up, attributes down" principle.

**Instead:** All cross-pane communication flows through the App/SyncController. Panes only know about their own data and the `CursorMoved` message contract.

### Anti-Pattern 2: Sync Logic Inside Pane Widgets

**What:** Putting relationship resolution or sync decisions inside the pane widgets themselves.

**Why bad:** Each pane would need to know about all other panes' data structures. Testing requires mocking three other panes. Adding a fifth pane means modifying four existing panes.

**Instead:** Panes only expose `sync_to(key)` and post `CursorMoved`. All relationship logic lives in resolver.py and sync.py.

### Anti-Pattern 3: Reactive Attributes for Cursor Sync

**What:** Using Textual's `reactive` + `data_bind` to propagate cursor position from App to panes.

**Why bad:** `data_bind` is one-way (parent to child) and triggers watch methods, which would need to move the cursor. But cursor moves in panes need to propagate *up* too (pane cursor move -> sync other panes). Mixing bidirectional flow through reactives creates confusion about who owns the cursor state. The cursor is owned by each pane; sync is a coordination concern, not a binding concern.

**Instead:** Use the message-based pattern: messages up (CursorMoved), method calls down (sync_to). Clear ownership, clear direction.

### Anti-Pattern 4: Propagation in Worker Threads

**What:** Running `propagate()` inside `_load_worktrees` worker thread.

**Why bad:** Propagation mutates `self._projects` which is app-level state. Mutating it from a background thread while the main thread reads it for rendering causes race conditions. Also, propagation needs both worktree AND terminal data, but the two workers are independent.

**Instead:** Propagation runs on the main thread after both `_set_worktrees` and `_set_terminal_sessions` have delivered their data.

---

## Data Flow: Complete Refresh Cycle

```
Timer fires (every 30s) or user presses 'r'
    |
    +-> _load_worktrees()  [worker thread]
    |       |
    |       +-> discover_worktrees() + fetch_mr_data()
    |       +-> call_from_thread(_set_worktrees)
    |               |
    |               +-> push data to WorktreePane
    |               +-> store live_worktrees on app
    |               +-> set _worktrees_ready = True
    |               +-> call _maybe_run_propagation()
    |
    +-> _load_terminal()  [worker thread]
            |
            +-> fetch_sessions()
            +-> call_from_thread(_set_terminal_sessions)
                    |
                    +-> push data to TerminalPane
                    +-> store live_sessions on app
                    +-> set _terminals_ready = True
                    +-> call _maybe_run_propagation()

_maybe_run_propagation()  [main thread, only runs when both ready]
    |
    +-> propagate(projects, worktrees, sessions, mr_data)
    |       |
    |       +-> returns PropagationResult (additions, removals, moves)
    |
    +-> if dirty: apply mutations to self._projects, save, refresh ProjectList
    |
    +-> build_index(projects, worktrees, sessions)
    |       |
    |       +-> returns RelationshipIndex
    |
    +-> sync_controller.update_index(index)
    |
    +-> _push_badge_counts()  -> ProjectList.set_badges()
```

## Data Flow: Cross-Pane Cursor Sync

```
User moves cursor in WorktreePane (j/k)
    |
    +-> _update_highlight() fires (existing)
    |
    +-> post_message(CursorMoved(key))  [new]
            |
            +-> bubbles to JoyApp
            +-> on_cursor_moved(message)
                    |
                    +-> sync_controller.handle_cursor_move(key, app)
                            |
                            +-> check: enabled? syncing? -> guard
                            +-> set _syncing = True
                            +-> lookup related items in index
                            +-> for each related pane:
                            |       +-> app.query_one(pane).sync_to(target_key)
                            |               |
                            |               +-> find row matching target_key
                            |               +-> set _cursor, _update_highlight()
                            |               +-> _update_highlight posts CursorMoved
                            |               +-> but _syncing is True -> no-op
                            +-> set _syncing = False
```

---

## Modifications to Existing Components

### app.py (JoyApp)

| Change | What | Why |
|--------|------|-----|
| New instance vars | `_sync_controller`, `_live_worktrees`, `_live_sessions`, `_worktrees_ready`, `_terminals_ready` | State for sync and propagation coordination |
| New binding | `S` for sync toggle | User control over sync behavior |
| Modified `_set_worktrees` | Store worktrees, set ready flag, call `_maybe_run_propagation()` | Trigger propagation when both sources ready |
| Modified `_set_terminal_sessions` | Store sessions, set ready flag, call `_maybe_run_propagation()` | Same |
| New method `_maybe_run_propagation` | Orchestrate propagation + index rebuild + badge push | Central coordination point |
| New method `_push_badge_counts` | Derive badge data from index, push to ProjectList | Badge counts depend on relationship index |
| New handler `on_cursor_moved` | Delegate to sync_controller | Entry point for cross-pane sync |

### widgets/project_list.py (ProjectList)

| Change | What | Why |
|--------|------|-----|
| Modified `ProjectRow.__init__` | Accept `badges` dict for worktree/agent counts | Badge display |
| New method `set_badges` | Update badge labels on existing rows without full rebuild | Efficient badge refresh |
| New method `sync_to` | Move cursor to project matching given ItemKey | Sync target |
| Modified `_update_highlight` | Post `CursorMoved` message after highlight | Sync source |

### widgets/worktree_pane.py (WorktreePane)

| Change | What | Why |
|--------|------|-----|
| New method `sync_to` | Move cursor to worktree row matching given ItemKey | Sync target |
| Modified `_update_highlight` | Post `CursorMoved` message after highlight | Sync source |
| Store `ItemKey` on each `WorktreeRow` | `WorktreeRow` gets a `key` attribute: `ItemKey("worktree", f"{repo_name}:{branch}")` | For sync_to lookup |

### widgets/terminal_pane.py (TerminalPane)

| Change | What | Why |
|--------|------|-----|
| New method `sync_to` | Move cursor to session row matching given ItemKey | Sync target |
| Modified `_update_highlight` | Post `CursorMoved` message after highlight | Sync source |
| Store `ItemKey` on each `SessionRow` | `SessionRow` gets a `key` attribute: `ItemKey("terminal", session_id)` | For sync_to lookup |

### widgets/project_detail.py (ProjectDetail)

| Change | What | Why |
|--------|------|-----|
| None for sync | Detail pane is passive -- it updates when ProjectList cursor moves (existing `on_project_list_project_highlighted`) | No additional sync needed; detail follows project selection |

### models.py

| Change | What | Why |
|--------|------|-----|
| No changes | ItemKey lives in resolver.py, not models.py | Keep models.py pure data; ItemKey is a sync/resolver concern |

### store.py

| Change | What | Why |
|--------|------|-----|
| No changes | Propagator calls existing `save_projects` | No new persistence needs |

---

## New Components Summary

| File | Type | Lines (est.) | Purpose |
|------|------|-------------|---------|
| `src/joy/resolver.py` | New module | ~120 | ItemKey, RelationshipIndex, build_index() |
| `src/joy/sync.py` | New module | ~80 | SyncController, CursorMoved message |
| `src/joy/propagator.py` | New module | ~200 | PropagationResult, propagate() |
| `tests/test_resolver.py` | New test | ~150 | Unit tests for relationship resolution |
| `tests/test_sync.py` | New test | ~100 | Unit tests for sync controller |
| `tests/test_propagator.py` | New test | ~200 | Unit tests for live data propagation |

---

## Suggested Build Order

Build order follows dependencies -- each phase produces testable, shippable increments.

### Phase 1: Resolver + Index
- Create `resolver.py` with ItemKey, RelationshipIndex, build_index()
- Write `test_resolver.py` -- pure unit tests, no Textual
- **Why first:** Everything else depends on the relationship index. Test it in isolation before wiring into the app.

### Phase 2: Badge Counts
- Modify ProjectRow to accept and display badge data
- Add `set_badges()` to ProjectList
- Wire `_push_badge_counts()` in JoyApp after index rebuild
- **Why second:** Badges are visible proof the index works, but don't require sync or propagation. Validates the index in production without the sync complexity.

### Phase 3: Sync Controller + Cross-Pane Sync
- Create `sync.py` with SyncController and CursorMoved message
- Add `sync_to()` to all three panes
- Modify `_update_highlight()` in all three panes to post CursorMoved
- Wire sync toggle (S key) in JoyApp
- **Why third:** Depends on resolver (Phase 1). Sync is the most user-visible v1.2 feature and should be tested interactively before propagation adds data mutations.

### Phase 4: Live Data Propagation
- Create `propagator.py` with propagate()
- Wire `_maybe_run_propagation()` in JoyApp
- Add ready-flag coordination to `_set_worktrees` and `_set_terminal_sessions`
- **Why last:** Most complex, most risk. Mutates projects.toml. Should only be added after the refresh/sync pipeline is proven stable.

---

## Scalability Considerations

| Concern | Current (v1.1) | After v1.2 | At Scale |
|---------|----------------|------------|----------|
| Refresh cost | 2 workers: git CLI + iTerm2 API | Same workers + ~1ms propagation + ~1ms index build on main thread | No change until >100 repos |
| Cursor sync latency | N/A | Synchronous on main thread, sub-ms | O(n) lookup in index; at 1000 items, still <1ms |
| Memory | Project + worktree data in memory | +RelationshipIndex (dict of sets, ~1KB for 50 items) | Negligible |
| TOML write frequency | On user action only | +after propagation (if dirty) | At most once per refresh (30s). Atomic write is ~1ms |

---

## Sources

- Textual Events/Messages guide: https://textual.textualize.io/guide/events/
- Textual Reactivity guide (data_bind, watch): https://textual.textualize.io/guide/reactivity/
- Textual message_pump API (prevent()): https://textual.textualize.io/api/message_pump/
- Textual Workers guide: https://textual.textualize.io/guide/workers/
- Textual Widgets guide: https://textual.textualize.io/guide/widgets/
- Existing joy codebase: app.py, project_list.py, worktree_pane.py, terminal_pane.py, project_detail.py, models.py, store.py
