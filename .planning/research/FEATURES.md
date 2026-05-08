# Feature Landscape: Frontend/Backend Separation (v1.4)

**Domain:** Ports & Adapters refactoring of existing Python TUI (Textual 8.x, ~7,400 LOC)
**Researched:** 2026-05-07
**Mode:** Refactoring existing app, not greenfield

## Context: What Exists Today

The current `app.py` is a 1,058-LOC monolith with 21 instance variables acting as a god class. It:
- Holds all application state (`_projects`, `_repos`, `_config`, `_rel_index`, `_current_worktrees`, `_current_sessions`, `_current_mr_data`, etc.)
- Directly accesses widget private fields (`detail._project`, `detail._rows`, `pane._cursor`, `pane._rows`, `project_list._cursor`, `project_list._rows`)
- Embeds business logic (MR auto-add in `_propagate_mr_auto_add`, sync guards via `_is_syncing`, badge computation)
- Manages all background data fetching (`_load_worktrees`, `_load_terminal`, `_load_data`)
- Orchestrates 6-direction cross-pane sync (`_sync_from_project`, `_sync_from_worktree`, `_sync_from_session`)
- Handles all CRUD operations (project create/delete/archive, object add/edit/delete)
- Manages timer lifecycle (`_refresh_timer`, `_label_timer`)
- Accesses `RelationshipIndex` private fields (`_rel_index._project_for_wt_path.keys()`)

Widgets already have partial public APIs (`set_projects`, `sync_to`, `clear_selection`, `update_badges`, `set_worktrees`, `set_sessions`), but app.py bypasses them when convenient.

---

## Table Stakes

Features the refactored architecture MUST deliver. Missing any of these means the refactoring is incomplete or harmful.

| # | Feature | Why Required | Complexity | Dependencies |
|---|---------|-------------|------------|--------------|
| TS-01 | **Protocol-based service contracts** | Without formal interfaces, the "separation" is just moving code around. Python `Protocol` classes define what the backend promises and what the frontend consumes. This is the atomic unit of Ports & Adapters. | Med | None -- foundational |
| TS-02 | **PaneCoordinator extraction** | The 6-direction cross-pane sync logic (lines 553-657 of app.py) is pure orchestration: given a highlighted item in pane A, tell panes B and C what to highlight. This is the single largest source of coupling. Extracting it as a plain Python class that receives pane facades and a RelationshipIndex means sync logic becomes unit-testable without any Textual imports. | High | TS-01, TS-06 |
| TS-03 | **DataOrchestrator extraction** | Background data loading (`_load_worktrees`, `_load_terminal`, `_load_data`), the two-flag readiness gate (`_worktrees_ready && _sessions_ready`), and the post-load cascade (`_maybe_compute_relationships` -> `_update_badges` -> `_propagate_changes` -> `_update_worktree_link_status`) is ~200 LOC of orchestration that has zero UI concern. Extract as a service that emits "data ready" events the app subscribes to. | High | TS-01, TS-04 |
| TS-04 | **ProjectService extraction** | CRUD operations on projects (create, rename, delete, archive/unarchive, add/edit/delete object) currently scattered across `action_new_project`, `_start_add_object_loop`, `_save_projects_bg`, `_append_to_archive_bg`, `_remove_from_archive_bg`. These are pure data operations that should be behind a service interface with no widget references. | Med | TS-01 |
| TS-05 | **Widget facade methods replacing private field access** | app.py reads `detail._project`, `detail._rows`, `pane._cursor`, `pane._rows`, `project_list._cursor`, `project_list._rows` -- 6 distinct private field accesses. Each widget needs a public facade: `current_project` property on ProjectDetail, `highlighted_item` property on each pane, `current_row_items` on ProjectDetail. Without these, any internal widget refactoring breaks app.py. | Low | None -- can be done incrementally |
| TS-06 | **Pane abstraction (SyncablePane protocol)** | The sync methods (`sync_to`, `clear_selection`) exist but are called ad-hoc. A `SyncablePane` protocol formalizes what PaneCoordinator needs from any pane: `sync_to(identity) -> bool`, `clear_selection() -> None`, and a `highlighted_identity` property. This protocol is what makes PaneCoordinator testable with fakes. | Low | TS-01 |
| TS-07 | **Backend service tests (fast, no TUI)** | PaneCoordinator, DataOrchestrator, and ProjectService must be testable as pure Python. This means: no `run_test()`, no Textual pilot, no async context managers -- just `pytest` with plain function calls and fake implementations of protocols. This is the primary value of the refactoring: making the complex logic testable without 240-second TUI test suites. | Med | TS-01 through TS-04 |
| TS-08 | **app.py reduced to thin Textual wrapper** | After extraction, app.py should contain ONLY: `compose()`, `on_mount()`, Textual message handlers that delegate to services, `BINDINGS`, and timer setup. Target: under 300 LOC, under 10 instance variables. The remaining code is "wiring" -- connecting Textual events to service calls and service results to widget updates. | High | TS-02, TS-03, TS-04, TS-05 |
| TS-09 | **Sync guard moved into PaneCoordinator** | The `_is_syncing` boolean flag that prevents infinite sync loops is currently managed manually with try/finally blocks scattered across app.py (lines 232, 281, 367, 559, 598, 635). This guard logic belongs in PaneCoordinator as internal state, with a context manager or decorator pattern. | Low | TS-02 |
| TS-10 | **RelationshipIndex private field access eliminated** | app.py accesses `_rel_index._project_for_wt_path.keys()` and `_rel_index._project_for_wt_branch.keys()` directly (lines 406-407). RelationshipIndex needs a public `linked_paths()` and `linked_branches()` method. Small change but important for the "no private field access" invariant. | Low | None |
| TS-11 | **Existing behavior preservation** | Every feature from v1.0 through v1.3 must work identically after refactoring. No regressions in: cross-pane sync (6 directions), MR auto-add, badge counts, filter mode, archive browser, DISPATCH routing, virtual rows, cursor identity preservation, stale tab healing. The existing 9,210 lines of tests must all pass (minus the known-failing tests). | High | All of the above |
| TS-12 | **Fix known failing tests** | test_propagation.py::TestTerminalAutoRemove (references non-existent method) and test_sync.py terminal sync (4 tests) are known tech debt. These must be fixed as part of the refactoring, not carried forward. | Med | TS-02, TS-03 |

---

## Differentiators

Features that make this refactoring genuinely valuable beyond "just moving code." Not required but substantially improve codebase quality.

| # | Feature | Value Proposition | Complexity | Dependencies |
|---|---------|-------------------|------------|--------------|
| DF-01 | **Widget tests with fake backend** | After extraction, widgets can be tested by injecting a fake DataOrchestrator/ProjectService into the app, then driving the TUI with Textual pilot. Tests verify "given this data, does the UI render correctly" without real TOML files, git commands, or iTerm2 sessions. This catches rendering bugs that pure backend tests miss. | Med | TS-01 through TS-04, TS-07 |
| DF-02 | **Reactive data flow (push, not pull)** | Currently app.py calls `pane.set_worktrees(data)` imperatively after each load. A reactive pattern where DataOrchestrator publishes state changes and widgets subscribe via Textual's `watch()` mechanism would eliminate the manual push cascade. Textual's reactive attributes are built for this. However, this may be over-engineering for the current complexity. | High | TS-03 |
| DF-03 | **Event-driven sync via Textual messages** | Instead of PaneCoordinator calling `pane.sync_to()` directly, sync could work through Textual messages: pane posts `PaneHighlighted(identity)`, PaneCoordinator handles it and posts `SyncRequest(target_pane, identity)`, target pane handles `SyncRequest`. This uses Textual's built-in message bubbling and is more idiomatic. | Med | TS-02, TS-06 |
| DF-04 | **Timer lifecycle in DataOrchestrator** | The refresh timer setup (`set_interval`, `_trigger_worktree_refresh`) and the label-update timer are currently in app.py. Moving timer management into DataOrchestrator centralizes the "when to refresh" decision and makes refresh-interval changes testable without TUI. | Low | TS-03 |
| DF-05 | **Action dispatcher extraction** | The `_open_first_of_kind` method + `_resolve_kind_value` + `_auto_create_kind` + `_prompt_for_kind` form a self-contained action dispatch system (~100 LOC). Extracting this into an ActionDispatcher service that takes the DISPATCH table, a ProjectService, and an OperationsService makes the keystroke-to-action pipeline testable independently. | Med | TS-04 |
| DF-06 | **UI audit and consistency fixes** | The milestone explicitly targets "fix UI bugs and visual inconsistencies across all panes." This means: consistent border styling, consistent cursor behavior when switching panes, consistent empty-state messages, consistent status bar feedback patterns. Not an architecture feature, but a quality-of-life deliverable that rides the refactoring. | Med | TS-11 |
| DF-07 | **Snapshot tests for visual regression** | Textual's pytest-textual-snap plugin generates SVG screenshots. A small set of snapshot tests (empty state, populated state, sync highlight state) would catch visual regressions during future refactoring. Use sparingly -- snapshot tests are brittle and slow, but 5-10 key states are worth capturing. | Low | DF-01 |

---

## Anti-Features

Features to explicitly NOT build during this refactoring. Each is tempting but counterproductive.

| # | Anti-Feature | Why Avoid | What to Do Instead |
|---|-------------|-----------|-------------------|
| AF-01 | **Dependency injection framework** | Libraries like `python-dependency-injector` or `inject` add complexity and magic. Python's Protocol + constructor injection is sufficient for this app's scale (~10 services). The overhead of a DI container is not justified for a personal tool with under 10K LOC. | Constructor injection: `JoyApp.__init__` creates concrete services and passes them to widgets/coordinators. Tests create fakes and pass those instead. |
| AF-02 | **Abstract base classes (ABCs)** | `abc.ABC` with `@abstractmethod` requires subclassing. Python `Protocol` (structural typing) achieves the same contract without inheritance coupling. Protocols are the Pythonic way since 3.8+. | Use `typing.Protocol` for all service contracts. |
| AF-03 | **Full reactive/observable pattern** | Converting all data flow to a reactive stream (RxPY, signals library) would be over-engineering. The app has ~5 data sources and ~5 consumers. Explicit push calls are fine at this scale. Textual's built-in `reactive` attribute handles the widget-level reactivity already. | Keep the DataOrchestrator as a service that calls explicit methods on the app when data is ready. Use Textual reactive attributes only within individual widgets. |
| AF-04 | **Event bus / pub-sub infrastructure** | A generic event bus (e.g., `blinker`, `pypubsub`) adds indirection without benefit. Textual already has a message system. The cross-pane sync is between exactly 3 panes -- not a "many publishers, many subscribers" pattern that justifies a bus. | Use Textual's built-in message system for widget-to-app communication. Use direct method calls for app-to-service and service-to-app communication. |
| AF-05 | **Repository pattern wrapping store.py** | store.py already IS the repository. It has `load_projects()`, `save_projects()`, `load_config()`, `save_config()`. Wrapping it in a Repository class with the same methods adds a layer of indirection with zero benefit. | Keep store.py as-is. ProjectService calls store functions directly. The "port" is the ProjectService protocol; store.py is the adapter. |
| AF-06 | **Splitting into separate Python packages** | The app is ~7,400 LOC. Splitting into `joy-core`, `joy-tui`, `joy-services` packages adds packaging complexity (multiple pyproject.toml, cross-package imports, version coordination) for no real isolation benefit. | Keep everything in `src/joy/` with clear module boundaries: `services/`, `protocols/`, `widgets/`, `screens/`. Directory structure enforces separation; package boundaries are overkill. |
| AF-07 | **Rewriting widgets during refactoring** | The temptation to "fix" widget internals (e.g., replace the manual cursor pattern with Textual's OptionList, rewrite ProjectList to use DataTable) is strong. But the goal is separation, not rewrite. Widget rewrites change behavior and require extensive re-testing. | Add facade methods to existing widgets. Refactor widget internals in a future milestone AFTER the architecture boundary is stable. |
| AF-08 | **Plugin/extension API** | The PROJECT.md explicitly lists this as out of scope. The modular architecture naturally supports future extensibility, but building plugin hooks now is premature. | Design clean Protocol boundaries that COULD become plugin interfaces later, but do not expose them publicly. |
| AF-09 | **Async service layer** | Making services `async def` to match Textual's event loop sounds clean but forces all tests to be async and adds `await` ceremony everywhere. The existing pattern of `@work(thread=True)` for I/O and `call_from_thread` for UI updates works well. Services should be synchronous; threading is the app's concern. | Services are synchronous Python classes. app.py wraps service calls in `@work(thread=True)` when I/O is involved. This keeps services simple and tests fast. |
| AF-10 | **Migrating from manual cursor to Textual OptionList** | OptionList is Textual's built-in selectable list widget. Migrating would be cleaner long-term but is a behavioral change that risks regressions in cursor identity preservation, sync_to targeting, and virtual row rendering. | Keep existing cursor pattern. Add facade methods that hide the cursor implementation. Evaluate OptionList migration as a separate future milestone. |

---

## Feature Dependencies

```
TS-01 (Protocol contracts)
  |
  +---> TS-02 (PaneCoordinator)  ---> TS-09 (sync guard)
  |       |
  |       +---> TS-08 (thin app.py)
  |
  +---> TS-03 (DataOrchestrator) ---> TS-08 (thin app.py)
  |       |
  |       +---> DF-04 (timer lifecycle)
  |
  +---> TS-04 (ProjectService)   ---> TS-08 (thin app.py)
  |       |
  |       +---> DF-05 (action dispatcher)
  |
  +---> TS-06 (SyncablePane protocol) ---> TS-02 (PaneCoordinator)

TS-05 (widget facades) --- independent, incremental

TS-10 (RelationshipIndex public API) --- independent, small

TS-07 (backend tests) ---> TS-01 through TS-04

TS-11 (behavior preservation) ---> all table stakes

TS-12 (fix failing tests) ---> TS-02, TS-03

DF-01 (widget tests with fakes) ---> TS-01 through TS-04, TS-07
DF-06 (UI audit) ---> TS-11
DF-07 (snapshot tests) ---> DF-01
```

---

## MVP Recommendation

### Phase 1: Contracts + Facades (foundation)
1. **TS-01** Protocol-based service contracts -- define `ProjectServiceProtocol`, `DataOrchestratorProtocol`, `SyncablePaneProtocol`
2. **TS-05** Widget facade methods -- add `current_project`, `highlighted_item`, `current_items` to widgets, replacing all private field access from app.py
3. **TS-10** RelationshipIndex public API -- add `linked_paths()`, `linked_branches()` methods
4. **TS-06** SyncablePane protocol -- formalize `sync_to`, `clear_selection`, `highlighted_identity`

### Phase 2: Service extraction (core value)
5. **TS-04** ProjectService -- extract CRUD operations (lowest coupling, easiest win)
6. **TS-03** DataOrchestrator -- extract background loading and readiness orchestration
7. **TS-02** PaneCoordinator -- extract 6-direction sync logic (highest value, highest complexity)
8. **TS-09** Sync guard in PaneCoordinator

### Phase 3: Thin app + tests
9. **TS-08** Reduce app.py to thin wrapper
10. **TS-07** Backend service tests with fake protocols
11. **TS-12** Fix known failing tests
12. **TS-11** Full regression pass

### Phase 4: Polish (differentiators)
13. **DF-01** Widget tests with fake backend
14. **DF-06** UI audit and consistency fixes
15. **DF-05** Action dispatcher extraction (optional, if time permits)

**Defer:** DF-02 (reactive data flow), DF-03 (event-driven sync), DF-04 (timer lifecycle in DataOrchestrator), DF-07 (snapshot tests). These are improvements that become easier after the architecture boundary is stable, but add risk during the initial extraction.

---

## Complexity Budget

| Component | Current LOC | Estimated LOC After | Extracted LOC | Notes |
|-----------|-------------|---------------------|---------------|-------|
| app.py | 1,058 | ~250-300 | -- | Target: under 300 LOC, under 10 instance variables |
| PaneCoordinator | -- | -- | ~150 | Pure Python, no Textual imports |
| DataOrchestrator | -- | -- | ~200 | Manages loading, readiness, relationships |
| ProjectService | -- | -- | ~120 | CRUD, archive, save operations |
| Protocols (contracts) | -- | -- | ~80 | Protocol classes + type definitions |
| Widget facade additions | -- | ~+30 per widget | -- | Properties replacing private field access |
| New backend tests | -- | -- | ~400 | PaneCoordinator + DataOrchestrator + ProjectService |
| **Total new code** | -- | -- | **~950** | Excluding tests |

The refactoring should roughly break even on total LOC (extracting ~750 from app.py, creating ~950 in services + protocols) but dramatically improve testability and maintainability.

---

## Specific Coupling Points to Break

These are the exact lines in app.py where the refactoring boundary matters most:

| Line(s) | Coupling | Extraction Target | Facade Needed |
|---------|----------|-------------------|---------------|
| 371-372 | `project_list._cursor`, `project_list._rows[...].project` | PaneCoordinator | `project_list.current_project` property |
| 676 | `detail._project` | Action handlers | `detail.current_project` property |
| 681 | `detail._rows` iteration for defaults | Action handlers | `detail.default_items` property |
| 810 | `detail._project` (dispatch) | ActionDispatcher | `detail.current_project` property |
| 912-915 | `pane._cursor`, `pane._rows` | Action handlers | `worktree_pane.highlighted_path` property |
| 406-407 | `_rel_index._project_for_wt_path.keys()` | DataOrchestrator | `rel_index.linked_paths()` method |
| 232, 281, 367, 559, 598, 635 | `_is_syncing` manual try/finally | PaneCoordinator | Internal state + context manager |
| 295-298 | `_worktrees_ready`, `_sessions_ready` flags | DataOrchestrator | Internal readiness gate |
| 311-347 | `_propagate_mr_auto_add` business logic | DataOrchestrator or ProjectService | Pure function, no widget refs |

---

## Sources

- Textual message passing and custom messages: https://textual.textualize.io/guide/events/
- Textual reactive attributes: https://textual.textualize.io/guide/reactivity/
- Textual worker threads: https://textual.textualize.io/guide/workers/
- Textual testing guide: https://textual.textualize.io/guide/testing/
- Python Protocol typing: https://docs.python.org/3/library/typing.html#typing.Protocol
- Mediator pattern for GUI coordination: https://refactoring.guru/design-patterns/mediator/python/example
- Hexagonal Architecture in Python: https://blog.szymonmiks.pl/p/hexagonal-architecture-in-python/
- Python dependency injection patterns: https://testdriven.io/blog/python-dependency-injection/
- Direct codebase analysis of app.py, widgets/, screens/, resolver.py, store.py, dispatch.py, models.py
